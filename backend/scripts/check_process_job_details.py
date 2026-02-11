#!/usr/bin/env python3
"""Check process job details."""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import get_firestore_client, init_firestore

PROCESS_JOB_ID = "svcx9H3sqfuC3D4dH1ug"
TRANSFER_JOB_ID = "fnfOqA3U32u0o8JUG1qh"


def main():
    init_firestore()
    firestore_client = get_firestore_client()
    
    print("=" * 60)
    print("检查压制任务详情")
    print("=" * 60)
    
    job_ref = firestore_client.collection("pipeline_jobs").document(PROCESS_JOB_ID)
    snapshot = job_ref.get()
    
    if snapshot.exists:
        data = snapshot.to_dict() or {}
        print(f"Job ID: {PROCESS_JOB_ID}")
        print(f"drama_name: {data.get('drama_name')}")
        print(f"status: {data.get('status')}")
        print(f"stage: {data.get('stage')}")
        print(f"created_at: {data.get('created_at')}")
        print(f"updated_at: {data.get('updated_at')}")
        print(f"transfer_completed: {data.get('transfer_completed')}")
        print(f"progress: {data.get('progress')}")
        print(f"total_files: {data.get('total_files')}")
        print(f"processed_files: {data.get('processed_files')}")
        print(f"failed_files: {data.get('failed_files')}")
        
        # Check if there's a related transfer job
        print("\n检查关联的传输任务:")
        transfer_ref = firestore_client.collection("pipeline_jobs").document(TRANSFER_JOB_ID)
        transfer_snapshot = transfer_ref.get()
        if transfer_snapshot.exists:
            transfer_data = transfer_snapshot.to_dict() or {}
            print(f"传输任务完成时间: {transfer_data.get('updated_at')}")
            print(f"压制任务创建时间: {data.get('created_at')}")
            
            if data.get('created_at') and transfer_data.get('updated_at'):
                import time
                created_ts = data.get('created_at').timestamp() if hasattr(data.get('created_at'), 'timestamp') else 0
                transfer_ts = transfer_data.get('updated_at').timestamp() if hasattr(transfer_data.get('updated_at'), 'timestamp') else 0
                delay = created_ts - transfer_ts
                print(f"延迟时间: {delay/60:.1f} 分钟")
    else:
        print(f"❌ Job {PROCESS_JOB_ID} 不存在")


if __name__ == "__main__":
    main()


