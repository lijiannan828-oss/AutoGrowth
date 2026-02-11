"""手动清理指定任务并触发下一个排队任务

使用方法:
    python -m backend.scripts.manual_cleanup_job <job_id>
    
示例:
    python -m backend.scripts.manual_cleanup_job NU3xvcuvxzutenLi5BNX
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import get_firestore_client, init_firestore
from app.services.concurrency_service import ConcurrencyService
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from google.cloud import firestore


def manual_cleanup_job(job_id: str):
    """手动清理指定任务并触发下一个排队任务"""
    print("=" * 60)
    print(f"手动清理任务: {job_id}")
    print("=" * 60)
    
    init_firestore()
    firestore_client = get_firestore_client()
    service = ConcurrencyService()
    
    # 1. 检查当前状态
    print("\n1. 检查当前状态...")
    concurrency_ref = firestore_client.collection("system_config").document("concurrency_control")
    concurrency_doc = concurrency_ref.get()
    
    if concurrency_doc.exists:
        data = concurrency_doc.to_dict() or {}
        running_jobs = data.get('running_job_ids', [])
        queue = data.get('queue', [])
        
        print(f"   运行中的任务: {running_jobs}")
        print(f"   排队中的任务: {queue}")
        
        if job_id in running_jobs:
            print(f"   ✅ 任务 {job_id} 在运行列表中")
        else:
            print(f"   ⚠️  任务 {job_id} 不在运行列表中")
            print("   可能已经被清理了")
            return False
    
    # 2. 检查任务状态
    print(f"\n2. 检查任务 {job_id} 状态...")
    job_ref = firestore_client.collection("pipeline_jobs").document(job_id)
    job_doc = job_ref.get()
    
    if job_doc.exists:
        job_data = job_doc.to_dict() or {}
        status = job_data.get('status', 'UNKNOWN')
        progress = job_data.get('progress', '')
        
        print(f"   当前状态: {status}")
        print(f"   进度: {progress[:80] if progress else 'N/A'}")
    else:
        print(f"   ⚠️  任务文档不存在")
    
    # 3. 手动清理
    print(f"\n3. 执行手动清理...")
    
    # 使用 release_and_trigger_next 来清理并触发下一个
    try:
        result = service.release_and_trigger_next(job_id)
        print(f"   ✅ 清理并触发下一个任务: {result}")
    except Exception as e:
        print(f"   ⚠️  release_and_trigger_next 失败: {e}")
        print(f"   尝试直接清理...")
        
        # 直接清理
        try:
            # 从 running_job_ids 中移除
            @firestore.transactional
            def remove_job_transaction(transaction):
                snapshot = concurrency_ref.get(transaction=transaction)
                if snapshot.exists:
                    data = snapshot.to_dict() or {}
                    running_jobs = data.get('running_job_ids', [])
                    if job_id in running_jobs:
                        running_jobs.remove(job_id)
                        transaction.update(concurrency_ref, {
                            'running_job_ids': running_jobs,
                        })
                        return True
                return False
            
            transaction = firestore_client.transaction()
            removed = remove_job_transaction(transaction)
            
            if removed:
                print(f"   ✅ 从 running_job_ids 中移除")
                
                # 更新任务状态
                if job_doc.exists:
                    job_ref.update({
                        'status': 'FAILED',
                        'progress': '任务已手动清理',
                        'updated_at': SERVER_TIMESTAMP,
                    })
                    print(f"   ✅ 更新任务状态为 FAILED")
                
                # 触发下一个任务
                try:
                    next_job = service.try_trigger_next_job(job_id)
                    if next_job:
                        print(f"   ✅ 触发下一个任务: {next_job}")
                    else:
                        print(f"   ⚠️  没有下一个任务可触发")
                except Exception as e:
                    print(f"   ⚠️  触发下一个任务失败: {e}")
            else:
                print(f"   ⚠️  任务不在 running_job_ids 中")
        except Exception as e:
            print(f"   ❌ 清理失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # 4. 检查清理后的状态
    print(f"\n4. 检查清理后的状态...")
    concurrency_doc = concurrency_ref.get()
    
    if concurrency_doc.exists:
        data = concurrency_doc.to_dict() or {}
        running_jobs_after = data.get('running_job_ids', [])
        queue_after = data.get('queue', [])
        
        print(f"   运行中的任务: {running_jobs_after}")
        print(f"   排队中的任务: {queue_after}")
        
        if job_id not in running_jobs_after:
            print(f"   ✅ 任务 {job_id} 已从运行列表中移除")
        else:
            print(f"   ⚠️  任务 {job_id} 仍在运行列表中")
        
        if len(queue) > len(queue_after):
            print(f"   ✅ 有任务从队列中移出（可能被触发）")
        elif len(running_jobs_after) > len(running_jobs):
            print(f"   ✅ 有新任务被触发")
        else:
            print(f"   ⚠️  没有任务被自动触发")
    
    print("\n" + "=" * 60)
    print("清理完成")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='手动清理指定任务并触发下一个排队任务')
    parser.add_argument('job_id', help='要清理的任务 ID')
    
    args = parser.parse_args()
    
    # 检查认证
    creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds:
        print("⚠️  警告: GOOGLE_APPLICATION_CREDENTIALS 未设置")
        print("   可能需要 GCP 认证才能访问 Firestore")
        print()
    
    success = manual_cleanup_job(args.job_id)
    sys.exit(0 if success else 1)

