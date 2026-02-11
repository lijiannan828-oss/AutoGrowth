#!/usr/bin/env python3
"""Check if process job was created for a transfer job."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.firestore import init_firestore, get_firestore_client
from datetime import datetime, timedelta

TRANSFER_JOB_ID = "aPUavEyOvn55TRdUwnpY"

init_firestore()
firestore = get_firestore_client()

# Get transfer job
transfer_job = firestore.collection("pipeline_jobs").document(TRANSFER_JOB_ID).get()
if not transfer_job.exists:
    print(f"❌ Transfer job {TRANSFER_JOB_ID} not found")
    sys.exit(1)

transfer_data = transfer_job.to_dict() or {}
drama_name = transfer_data.get("drama_name", "").strip()
transfer_completed_at = transfer_data.get("updated_at")

print(f"Transfer Job: {TRANSFER_JOB_ID}")
print(f"Drama Name: {drama_name}")
print(f"Transfer Completed At: {transfer_completed_at}")
print()

# Find all process jobs for this drama created after transfer completion
print("Searching for process jobs...")
all_jobs = firestore.collection("pipeline_jobs").where("drama_name", "==", drama_name).stream()

process_jobs = []
for job in all_jobs:
    data = job.to_dict() or {}
    stage = data.get("stage")
    created_at = data.get("created_at")
    
    if stage == 2:  # Process job
        process_jobs.append((job.id, data, created_at))

# Sort by created_at
process_jobs.sort(key=lambda x: x[2] if x[2] else datetime.min, reverse=True)

print(f"Found {len(process_jobs)} process job(s)")
print()

if process_jobs:
    # Check if any were created after transfer completion
    if transfer_completed_at:
        recent_jobs = [
            (job_id, data, created_at)
            for job_id, data, created_at in process_jobs
            if created_at and isinstance(created_at, datetime) and transfer_completed_at and isinstance(transfer_completed_at, datetime) and created_at >= transfer_completed_at
        ]
        
        if recent_jobs:
            print("✅ Found process job(s) created after transfer completion:")
            for job_id, data, created_at in recent_jobs:
                print(f"\n  Job ID: {job_id}")
                print(f"    Created: {created_at}")
                print(f"    Status: {data.get('status', 'N/A')}")
                print(f"    Total Files: {data.get('total_files', 'N/A')}")
                print(f"    Processed: {data.get('processed_files', 0)}")
                print(f"    Failed: {data.get('failed_files', 0)}")
        else:
            print("⚠️  No process jobs created after transfer completion")
            print("\n  Most recent process job:")
            if process_jobs:
                job_id, data, created_at = process_jobs[0]
                print(f"    Job ID: {job_id}")
                print(f"    Created: {created_at}")
                print(f"    Status: {data.get('status', 'N/A')}")
    else:
        print("⚠️  Cannot determine transfer completion time")
        print("\n  Most recent process job:")
        if process_jobs:
            job_id, data, created_at = process_jobs[0]
            print(f"    Job ID: {job_id}")
            print(f"    Created: {created_at}")
            print(f"    Status: {data.get('status', 'N/A')}")
else:
    print("❌ No process jobs found for this drama")


