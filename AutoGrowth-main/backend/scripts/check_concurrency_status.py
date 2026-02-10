#!/usr/bin/env python3
"""检查并发控制状态"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.firestore import init_firestore, get_firestore_client

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
        print(f"🔒 并发控制状态:")
        print(f"  max_concurrent_jobs: {concurrency_data.get('max_concurrent_jobs', 'N/A')}")
        print(f"  running_job_ids: {concurrency_data.get('running_job_ids', [])}")
        print(f"  queue: {concurrency_data.get('queue', [])}")
        print(f"  updated_at: {concurrency_data.get('updated_at', 'N/A')}")
        
        running_job_ids = concurrency_data.get('running_job_ids', [])
        queue = concurrency_data.get('queue', [])
        
        print(f"\n📊 状态分析:")
        print(f"  正在运行的任务数: {len(running_job_ids)}")
        print(f"  队列中的任务数: {len(queue)}")
        
        # 检查 job_id 是否在 running_job_ids 中
        if job_id in running_job_ids:
            print(f"\n⚠️  WARNING: Job {job_id} 在 running_job_ids 中，但状态是 QUEUED")
        else:
            print(f"\n✅ Job {job_id} 不在 running_job_ids 中")
        
        # 检查 job_id 是否在 queue 中
        if job_id in queue:
            position = queue.index(job_id) + 1
            print(f"⚠️  Job {job_id} 在 queue 中，位置: {position}")
        else:
            print(f"✅ Job {job_id} 不在 queue 中")
        
        # 检查正在运行的任务状态
        if running_job_ids:
            print(f"\n🔍 检查正在运行的任务状态:")
            for running_job_id in running_job_ids:
                job_ref = firestore.collection("pipeline_jobs").document(running_job_id)
                job_snapshot = job_ref.get()
                if job_snapshot.exists:
                    job_data = job_snapshot.to_dict() or {}
                    status = job_data.get('status', 'N/A')
                    print(f"  {running_job_id}: status={status}")
                else:
                    print(f"  {running_job_id}: ❌ 文档不存在")
    else:
        print("❌ 并发控制文档不存在")

if __name__ == "__main__":
    main()

