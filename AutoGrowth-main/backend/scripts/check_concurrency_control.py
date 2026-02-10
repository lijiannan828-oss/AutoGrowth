#!/usr/bin/env python3
"""Check concurrency control document status."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import get_firestore_client, init_firestore
from app.services.concurrency_service import CONCURRENCY_CONTROL_COLLECTION, CONCURRENCY_CONTROL_DOC


def main():
    """Check concurrency control document status."""
    init_firestore()
    
    firestore_client = get_firestore_client()
    control_ref = firestore_client.collection(CONCURRENCY_CONTROL_COLLECTION).document(CONCURRENCY_CONTROL_DOC)
    snapshot = control_ref.get()
    
    if not snapshot.exists:
        print("⚠️  Concurrency control document does not exist")
        print("   This is normal if no jobs have been triggered yet.")
        return
    
    data = snapshot.to_dict() or {}
    running_jobs = data.get("running_jobs", 0)
    running_job_ids = data.get("running_job_ids", [])
    queue = data.get("queue", [])
    updated_at = data.get("updated_at")
    
    print("=" * 60)
    print("📊 Concurrency Control Status")
    print("=" * 60)
    print(f"Running Jobs: {running_jobs}")
    print(f"Running Job IDs: {running_job_ids}")
    print(f"Queue Size: {len(queue)}")
    print(f"Queue: {queue}")
    print(f"Last Updated: {updated_at}")
    print("=" * 60)
    
    # Check if running jobs match the list
    if running_jobs != len(running_job_ids):
        print("⚠️  WARNING: running_jobs count doesn't match running_job_ids length")
    
    # Check queue order
    if queue:
        print(f"\n📋 Queue Order (FIFO):")
        for i, job_id in enumerate(queue, 1):
            print(f"  {i}. {job_id}")


if __name__ == "__main__":
    main()


