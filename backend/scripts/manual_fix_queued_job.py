#!/usr/bin/env python3
"""手动修复 QUEUED 状态的任务"""

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
    
    # 检查任务状态
    job_ref = firestore.collection("pipeline_jobs").document(job_id)
    job_snapshot = job_ref.get()
    
    if not job_snapshot.exists:
        print(f"❌ Job {job_id} 不存在")
        return
    
    job_data = job_snapshot.to_dict() or {}
    status = job_data.get('status', 'N/A')
    print(f"📋 Job {job_id} 当前状态: {status}")
    
    # 检查并发控制状态
    concurrency_ref = firestore.collection("system_config").document("concurrency_control")
    concurrency_snapshot = concurrency_ref.get()
    
    running_job_ids = []
    queue = []
    
    if concurrency_snapshot.exists:
        concurrency_data = concurrency_snapshot.to_dict() or {}
        running_job_ids = concurrency_data.get('running_job_ids', [])
        queue = concurrency_data.get('queue', [])
        print(f"\n🔒 并发控制状态:")
        print(f"  running_job_ids: {running_job_ids}")
        print(f"  queue: {queue}")
    
    # 检查任务是否在 queue 或 running_job_ids 中
    in_queue = job_id in queue
    in_running = job_id in running_job_ids
    
    print(f"\n🔍 状态检查:")
    print(f"  任务在 queue 中: {in_queue}")
    print(f"  任务在 running_job_ids 中: {in_running}")
    
    if status == "QUEUED":
        if not in_queue and not in_running:
            print(f"\n⚠️  问题: 任务状态是 QUEUED，但不在 queue 或 running_job_ids 中")
            print(f"   这是状态不一致的问题")
            
            # 更新状态为 FAILED
            print(f"\n🔄 更新任务状态为 FAILED...")
            job_ref.update({
                "status": "FAILED",
                "progress": "任务失败（旧代码版本，状态未正确更新）",
                "updated_at": SERVER_TIMESTAMP,
            })
            print(f"✅ 任务状态已更新为 FAILED")
            
            # 确保锁被释放
            if in_running:
                print(f"\n🔄 从 running_job_ids 中移除任务...")
                concurrency_service = ConcurrencyService()
                concurrency_service.release_job_slot(job_id)
                print(f"✅ 锁已释放")
        elif in_running:
            print(f"\n⚠️  问题: 任务在 running_job_ids 中，但状态是 QUEUED")
            print(f"   这是'僵尸任务'")
            
            # 更新状态为 FAILED
            print(f"\n🔄 更新任务状态为 FAILED...")
            job_ref.update({
                "status": "FAILED",
                "progress": "任务失败（僵尸任务，状态未正确更新）",
                "updated_at": SERVER_TIMESTAMP,
            })
            print(f"✅ 任务状态已更新为 FAILED")
            
            # 释放锁
            print(f"\n🔄 释放锁...")
            concurrency_service = ConcurrencyService()
            concurrency_service.release_job_slot(job_id)
            print(f"✅ 锁已释放")
            
            # 尝试触发下一个任务
            print(f"\n🔄 尝试触发下一个任务...")
            triggered = concurrency_service.try_trigger_next_job(job_id)
            if triggered:
                print(f"✅ 下一个任务已触发")
            else:
                print(f"ℹ️  没有待触发的任务")
        elif in_queue:
            position = queue.index(job_id) + 1
            print(f"\n✅ 任务在队列中，位置: {position}")
            print(f"   这是正常状态，等待执行")
    else:
        print(f"\n✅ 任务状态正常: {status}")

if __name__ == "__main__":
    main()

