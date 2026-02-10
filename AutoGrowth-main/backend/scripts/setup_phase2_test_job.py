#!/usr/bin/env python3
"""Setup test job for Phase 2 local integration testing.

This script creates a test job in Firestore for Phase 2 sharding integration test.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from app.core.firestore import get_firestore_client, init_firestore
from app.core.config import settings


def create_test_job(drama_name: str = "TEST_SHARDING_001") -> str:
    """Create a test job in Firestore for Phase 2 testing."""
    
    print("=" * 80)
    print("Phase 2 Test Job Setup")
    print("=" * 80)
    
    # Initialize Firestore
    init_firestore()
    client = get_firestore_client()
    
    # Create test job document
    job_ref = client.collection("pipeline_jobs").document()
    doc_body = {
        "drama_name": drama_name,
        "status": "QUEUED",
        "stage": 1,
        "type": "standard",
        "progress": "等待压制任务开始",
        "transfer_completed": True,
        "gcs_source_bucket": settings.pipeline_gcs_source_bucket,
        "gcs_processed_bucket": settings.pipeline_gcs_processed_bucket,
        "total_files": None,  # Will be set by worker or relay service
        "processed_files": 0,
        "failed_files": 0,
        "created_at": SERVER_TIMESTAMP,
        "updated_at": SERVER_TIMESTAMP,
        "created_by": "test-script",
        "created_by_name": "Phase 2 Test",
        "auth_mode": "dev_default",
        "last_event": {
            "type": "TEST_JOB_CREATED",
            "user": "test-script",
            "timestamp": SERVER_TIMESTAMP,
        },
    }
    
    job_ref.set(doc_body)
    job_id = job_ref.id
    
    print(f"\n✅ Created test job:")
    print(f"   Job ID: {job_id}")
    print(f"   Drama Name: {drama_name}")
    print(f"   Status: QUEUED")
    print(f"   Stage: 1")
    print(f"   Transfer Completed: True")
    print(f"\n📋 Firestore Console URL:")
    print(f"   https://console.cloud.google.com/firestore/databases/-default-/data/~2Fpipeline_jobs~2F{job_id}")
    print(f"\n🚀 Next Steps:")
    print(f"   1. Ensure GCS bucket '{settings.pipeline_gcs_source_bucket}' contains test drama '{drama_name}'")
    print(f"   2. Run Task 0: ./run_process_worker_local.sh {job_id} 0 2")
    print(f"   3. Run Task 1: ./run_process_worker_local.sh {job_id} 1 2")
    print(f"   4. Verify Firestore documents and logs")
    
    return job_id


if __name__ == "__main__":
    drama_name = sys.argv[1] if len(sys.argv) > 1 else "TEST_SHARDING_001"
    job_id = create_test_job(drama_name)
    print(f"\n✅ Test job created: {job_id}")


