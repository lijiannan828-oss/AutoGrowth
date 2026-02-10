#!/usr/bin/env python3
"""检查任务状态和并发控制状态"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.firestore import init_firestore, get_firestore_client

def main():
    job_id = "bXSjYya7FG3hIkP1qGx0"
    
    # 初始化 Firestore
    init_firestore()
    firestore = get_firestore_client()
    
    # 检查任务状态
    job_ref = firestore.collection("pipeline_jobs").document(job_id)
    job_snapshot = job_ref.get()
    
    if job_snapshot.exists:
        job_data = job_snapshot.to_dict() or {}
        print(f"📋 Job {job_id} 状态:")
        print(f"  status: {job_data.get('status', 'N/A')}")
        print(f"  progress: {job_data.get('progress', 'N/A')}")
        print(f"  total_files: {job_data.get('total_files', 'N/A')}")
        print(f"  processed_files: {job_data.get('processed_files', 'N/A')}")
        print(f"  failed_files: {job_data.get('failed_files', 'N/A')}")
        print(f"  updated_at: {job_data.get('updated_at', 'N/A')}")
    else:
        print(f"❌ Job {job_id} 不存在")
    
    # 检查并发控制状态
    concurrency_ref = firestore.collection("system_config").document("concurrency_control")
    concurrency_snapshot = concurrency_ref.get()
    
    if concurrency_snapshot.exists:
        concurrency_data = concurrency_snapshot.to_dict() or {}
        print(f"\n🔒 并发控制状态:")
        print(f"  running_job_ids: {concurrency_data.get('running_job_ids', [])}")
        print(f"  queue: {concurrency_data.get('queue', [])}")
        print(f"  max_concurrent_jobs: {concurrency_data.get('max_concurrent_jobs', 'N/A')}")
        
        # 检查 job_id 是否在 running_job_ids 中
        running_job_ids = concurrency_data.get('running_job_ids', [])
        if job_id in running_job_ids:
            print(f"\n⚠️  WARNING: Job {job_id} 仍在 running_job_ids 中！")
        else:
            print(f"\n✅ Job {job_id} 不在 running_job_ids 中")
        
        # 检查 job_id 是否在 queue 中
        queue = concurrency_data.get('queue', [])
        if job_id in queue:
            print(f"⚠️  WARNING: Job {job_id} 仍在 queue 中！")
        else:
            print(f"✅ Job {job_id} 不在 queue 中")
    else:
        print("\n❌ 并发控制文档不存在")

if __name__ == "__main__":
    main()

