#!/usr/bin/env python3
"""修复 QUEUED 状态的任务"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.firestore import init_firestore, get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from app.services.concurrency_service import ConcurrencyService

def main():
    job_id = "bXSjYya7FG3hIkP1qGx0"
    
    # 初始化 Firestore
    init_firestore()
    firestore = get_firestore_client()
    
    # 检查并发控制状态
    concurrency_ref = firestore.collection("system_config").document("concurrency_control")
    concurrency_snapshot = concurrency_ref.get()
    
    if concurrency_snapshot.exists:
        concurrency_data = concurrency_snapshot.to_dict() or {}
        running_job_ids = concurrency_data.get('running_job_ids', [])
        queue = concurrency_data.get('queue', [])
        max_concurrent = concurrency_data.get('max_concurrent_jobs', 1)
        
        print(f"🔒 并发控制状态:")
        print(f"  max_concurrent_jobs: {max_concurrent}")
        print(f"  running_job_ids: {running_job_ids}")
        print(f"  queue: {queue}")
        
        # 检查任务状态
        job_ref = firestore.collection("pipeline_jobs").document(job_id)
        job_snapshot = job_ref.get()
        
        if job_snapshot.exists:
            job_data = job_snapshot.to_dict() or {}
            status = job_data.get('status', 'N/A')
            print(f"\n📋 Job {job_id} 状态:")
            print(f"  status: {status}")
            print(f"  progress: {job_data.get('progress', 'N/A')}")
            
            # 检查任务是否在 queue 或 running_job_ids 中
            in_queue = job_id in queue
            in_running = job_id in running_job_ids
            
            print(f"\n🔍 状态检查:")
            print(f"  任务在 queue 中: {in_queue}")
            print(f"  任务在 running_job_ids 中: {in_running}")
            
            if status == "QUEUED":
                if not in_queue and not in_running:
                    print(f"\n⚠️  问题: 任务状态是 QUEUED，但不在 queue 或 running_job_ids 中")
                    print(f"   这可能是状态不一致的问题")
                    
                    # 尝试重新获取 slot
                    print(f"\n🔄 尝试重新获取 slot...")
                    concurrency_service = ConcurrencyService()
                    can_start, message = concurrency_service.acquire_job_slot(job_id)
                    
                    if can_start:
                        print(f"✅ 成功获取 slot: {message}")
                        print(f"   任务应该会被触发")
                    else:
                        print(f"⏳ 任务被加入队列: {message}")
                elif in_running:
                    print(f"\n⚠️  问题: 任务在 running_job_ids 中，但状态是 QUEUED")
                    print(f"   这可能是'僵尸任务'")
                    
                    # 检查 Cloud Run Job 是否真的在运行
                    print(f"\n🔍 检查 Cloud Run Job 执行状态...")
                    # 这里需要检查 Cloud Run Job 的执行状态
                    # 如果不在运行，应该从 running_job_ids 中移除
                elif in_queue:
                    position = queue.index(job_id) + 1
                    print(f"\n✅ 任务在队列中，位置: {position}")
                    print(f"   当前运行的任务数: {len(running_job_ids)}/{max_concurrent}")
                    if len(running_job_ids) < max_concurrent:
                        print(f"   ⚠️  有可用 slot，但任务没有被触发")
                        print(f"   可能需要手动触发")
        else:
            print(f"❌ Job {job_id} 不存在")
    else:
        print("❌ 并发控制文档不存在")

if __name__ == "__main__":
    main()

