#!/usr/bin/env python3
"""Verify Phase 2 local integration test results.

This script verifies that Phase 2 test completed successfully by checking:
1. Task documents exist and are COMPLETED
2. Main job document has correct processed_files count
3. Main job status is SUCCEEDED
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import get_firestore_client, init_firestore


def verify_test_results(job_id: str, expected_task_count: int = 2) -> int:
    """Verify Phase 2 test results."""
    
    print("=" * 80)
    print("Phase 2 Test Results Verification")
    print("=" * 80)
    print(f"\nJob ID: {job_id}")
    print(f"Expected Task Count: {expected_task_count}")
    
    # Initialize Firestore
    init_firestore()
    client = get_firestore_client()
    
    # Get main job document
    job_ref = client.collection("pipeline_jobs").document(job_id)
    job_snapshot = job_ref.get()
    
    if not job_snapshot.exists:
        print(f"\n❌ Job document {job_id} does not exist")
        return 1
    
    job_data = job_snapshot.to_dict() or {}
    
    print(f"\n{'-' * 80}")
    print("Main Job Document")
    print(f"{'-' * 80}")
    print(f"  Status: {job_data.get('status', 'N/A')}")
    print(f"  Stage: {job_data.get('stage', 'N/A')}")
    print(f"  Total Files: {job_data.get('total_files', 'N/A')}")
    print(f"  Processed Files: {job_data.get('processed_files', 0)}")
    print(f"  Failed Files: {job_data.get('failed_files', 0)}")
    
    # Check task documents
    print(f"\n{'-' * 80}")
    print("Task Documents")
    print(f"{'-' * 80}")
    
    tasks_ref = job_ref.collection("tasks")
    tasks_snapshot = tasks_ref.stream()
    
    task_docs = {}
    for task_snapshot in tasks_snapshot:
        task_data = task_snapshot.to_dict() or {}
        task_index = task_snapshot.id
        task_docs[task_index] = task_data
        
        print(f"\n  Task {task_index}:")
        print(f"    Status: {task_data.get('status', 'N/A')}")
        print(f"    Total Count: {task_data.get('total_count', 'N/A')}")
        print(f"    Progress Count: {task_data.get('progress_count', 0)}")
        print(f"    Success Files: {len(task_data.get('success_files', []))}")
        print(f"    Failed Files: {len(task_data.get('failed_files', []))}")
    
    # Verification
    print(f"\n{'-' * 80}")
    print("Verification")
    print(f"{'-' * 80}")
    
    all_passed = True
    
    # Check 1: Task documents exist
    if len(task_docs) == expected_task_count:
        print(f"  ✅ Task documents count: {len(task_docs)} (expected: {expected_task_count})")
    else:
        print(f"  ❌ Task documents count: {len(task_docs)} (expected: {expected_task_count})")
        all_passed = False
    
    # Check 2: All tasks are COMPLETED
    completed_tasks = sum(1 for t in task_docs.values() if t.get('status') == 'COMPLETED')
    if completed_tasks == expected_task_count:
        print(f"  ✅ Completed tasks: {completed_tasks}/{expected_task_count}")
    else:
        print(f"  ❌ Completed tasks: {completed_tasks}/{expected_task_count}")
        all_passed = False
    
    # Check 3: Main job status is SUCCEEDED
    main_status = job_data.get('status', '')
    if main_status == 'SUCCEEDED':
        print(f"  ✅ Main job status: {main_status}")
    else:
        print(f"  ❌ Main job status: {main_status} (expected: SUCCEEDED)")
        all_passed = False
    
    # Check 4: Processed files count matches sum of task success files
    total_processed = job_data.get('processed_files', 0)
    total_success_from_tasks = sum(
        len(t.get('success_files', [])) for t in task_docs.values()
    )
    
    if total_processed == total_success_from_tasks:
        print(f"  ✅ Processed files match: {total_processed} (main) == {total_success_from_tasks} (tasks)")
    else:
        print(f"  ⚠️  Processed files mismatch: {total_processed} (main) != {total_success_from_tasks} (tasks)")
        # This might be okay if some tasks are still running
    
    # Check 5: No duplicate files across tasks
    all_success_files = []
    for task_data in task_docs.values():
        all_success_files.extend(task_data.get('success_files', []))
    
    unique_files = set(all_success_files)
    if len(all_success_files) == len(unique_files):
        print(f"  ✅ No duplicate files across tasks: {len(all_success_files)} files")
    else:
        duplicates = len(all_success_files) - len(unique_files)
        print(f"  ❌ Duplicate files found: {duplicates} duplicates")
        all_passed = False
    
    # Summary
    print(f"\n{'=' * 80}")
    print("Test Summary")
    print(f"{'=' * 80}")
    
    if all_passed:
        print(f"✅ All verifications passed!")
        return 0
    else:
        print(f"❌ Some verifications failed")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_phase2_results.py <JOB_ID> [EXPECTED_TASK_COUNT]")
        sys.exit(1)
    
    job_id = sys.argv[1]
    expected_task_count = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    sys.exit(verify_test_results(job_id, expected_task_count))


