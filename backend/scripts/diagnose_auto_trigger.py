#!/usr/bin/env python3
"""Diagnose automatic process job triggering after transfer completion.

This script checks:
1. Transfer job status in Firestore
2. GCS signal file (_PROCESS_NOW.txt) existence
3. Eventarc trigger configuration and recent events
4. Relay Service logs
5. Process job creation and status
6. File pairing accuracy
7. Sharding execution status
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from google.cloud import firestore, storage
try:
    from google.cloud import logging as cloud_logging
    HAS_LOGGING = True
except ImportError:
    HAS_LOGGING = False
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.firestore import init_firestore, get_firestore_client
from app.core.config import settings

# Configuration
PROJECT_ID = "fleet-blend-469520-n7"
REGION = "us-central1"  # Target service region
EVENTARC_REGION = "asia-northeast3"  # Eventarc trigger region
FIRESTORE_COLLECTION = "pipeline_jobs"
FAILURE_COLLECTION = "processing_failures"
TRANSFER_JOB_ID = "f7DTMToHvkNLqBe4Bl97"


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title: str):
    """Print a subsection header."""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print("─" * 80)


def check_transfer_job_status():
    """Check transfer job status in Firestore."""
    print_section("1. Transfer Job Status")
    
    init_firestore()
    firestore_client = get_firestore_client()
    job_ref = firestore_client.collection(FIRESTORE_COLLECTION).document(TRANSFER_JOB_ID)
    job_snapshot = job_ref.get()
    
    if not job_snapshot.exists:
        print(f"❌ Transfer job {TRANSFER_JOB_ID} does not exist in Firestore")
        return None
    
    job_data = job_snapshot.to_dict() or {}
    
    print(f"✅ Transfer job found: {TRANSFER_JOB_ID}")
    print(f"\n  Job Details:")
    print(f"    drama_name: {job_data.get('drama_name', 'N/A')}")
    print(f"    status: {job_data.get('status', 'N/A')}")
    print(f"    stage: {job_data.get('stage', 'N/A')}")
    print(f"    transfer_completed: {job_data.get('transfer_completed', False)}")
    print(f"    created_at: {job_data.get('created_at', 'N/A')}")
    print(f"    updated_at: {job_data.get('updated_at', 'N/A')}")
    
    # Check if transfer is completed
    transfer_completed = job_data.get("transfer_completed", False)
    stage = job_data.get("stage")
    
    if transfer_completed and (stage == 1 or stage is None):
        print(f"\n  ✅ Transfer is completed and ready for processing")
        print(f"     (transfer_completed=True, stage={stage})")
    else:
        print(f"\n  ⚠️  Transfer may not be ready for processing")
        print(f"     transfer_completed={transfer_completed}, stage={stage}")
    
    return job_data


def check_gcs_signal_file(job_data: dict | None):
    """Check if _PROCESS_NOW.txt signal file exists in GCS."""
    print_section("2. GCS Signal File (_PROCESS_NOW.txt)")
    
    if not job_data:
        print("⚠️  Skipping GCS check (no job data)")
        return False
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found in job data")
        return False
    
    source_bucket = job_data.get("gcs_source_bucket") or "vigloo_source"
    
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(source_bucket)
    
    # Check signal file path
    signal_path = f"{drama_name}/_PROCESS_NOW.txt"
    blob = bucket.blob(signal_path)
    
    print(f"  Checking signal file: gs://{source_bucket}/{signal_path}")
    
    if blob.exists():
        print(f"  ✅ Signal file exists")
        blob.reload()
        print(f"     Created: {blob.time_created}")
        print(f"     Updated: {blob.updated}")
        return True
    else:
        print(f"  ❌ Signal file does NOT exist")
        print(f"     This may be why Eventarc did not trigger")
        return False


def check_eventarc_trigger():
    """Check Eventarc trigger configuration."""
    print_section("3. Eventarc Trigger Configuration")
    
    import subprocess
    
    try:
        # List Eventarc triggers (check both regions)
        for check_region in [EVENTARC_REGION, REGION]:
            result = subprocess.run(
                [
                    "gcloud", "eventarc", "triggers", "list",
                    "--location", check_region,
                    "--project", PROJECT_ID,
                    "--format", "json"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                import json
                triggers = json.loads(result.stdout)
                
                if triggers:
                    print(f"  ✅ Found {len(triggers)} Eventarc trigger(s) in {check_region}")
                    for trigger in triggers:
                        name = trigger.get("name", "N/A")
                        destination = trigger.get("destination", {})
                        # FIX: Use correct field path: destination.cloudRun (not cloudRunService)
                        cloud_run = destination.get("cloudRun", {})
                        run_service = cloud_run.get("service", "N/A")
                        run_region = cloud_run.get("region", "N/A")
                        run_path = cloud_run.get("path", "N/A")
                        filters = trigger.get("eventFilters", [])
                        
                        print(f"\n  Trigger: {name} (region: {check_region})")
                        print(f"    Destination: {run_service} ({run_region})")
                        print(f"    Path: {run_path}")
                        print(f"    Filters:")
                        for f in filters:
                            print(f"      {f.get('attribute', 'N/A')}={f.get('value', 'N/A')}")
                        
                        # Check if it's configured for _PROCESS_NOW.txt
                        path_pattern = next(
                            (f.get("value") for f in filters if f.get("attribute") == "subject"),
                            None
                        )
                        if path_pattern and "_PROCESS_NOW.txt" in path_pattern:
                            print(f"    ✅ Configured for _PROCESS_NOW.txt")
                        else:
                            print(f"    ⚠️  May not be configured for _PROCESS_NOW.txt")
                    break  # Found triggers, no need to check other region
                else:
                    if check_region == REGION:
                        print(f"  ⚠️  No Eventarc triggers found in {check_region}")
            else:
                if check_region == REGION:
                    print(f"  ⚠️  Failed to list triggers in {check_region}: {result.stderr}")
    
    except Exception as exc:
        print(f"  ⚠️  Error checking Eventarc triggers: {exc}")


def check_relay_service_logs(job_data: dict | None):
    """Check Relay Service logs for recent activity."""
    print_section("4. Relay Service Logs")
    
    if not HAS_LOGGING:
        print("⚠️  Cloud Logging library not available, skipping log check")
        print("     Install with: pip install google-cloud-logging")
        return
    
    if not job_data:
        print("⚠️  Skipping log check (no job data)")
        return
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found")
        return
    
    try:
        logging_client = cloud_logging.Client(project=PROJECT_ID)
        
        # Query recent logs from relay service
        filter_str = (
            f'resource.type="cloud_run_revision" '
            f'AND resource.labels.service_name="drama-processor-relay-service" '
            f'AND textPayload=~"{drama_name}"'
        )
        
        print(f"  Querying logs for drama: {drama_name}")
        print(f"  Filter: {filter_str}")
        
        entries = logging_client.list_entries(
            filter_=filter_str,
            max_results=20,
            order_by=cloud_logging.DESCENDING
        )
        
        entries_list = list(entries)
        
        if entries_list:
            print(f"\n  ✅ Found {len(entries_list)} recent log entries")
            print(f"\n  Recent logs:")
            for entry in entries_list[:10]:
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "N/A"
                payload = entry.payload if hasattr(entry, 'payload') else str(entry)
                print(f"    [{timestamp}] {payload}")
        else:
            print(f"  ⚠️  No recent logs found for drama: {drama_name}")
            print(f"     This may indicate Relay Service was not triggered")
    
    except Exception as exc:
        print(f"  ⚠️  Error checking logs: {exc}")


def check_process_jobs(job_data: dict | None):
    """Check if process jobs were created."""
    print_section("5. Process Jobs Status")
    
    if not job_data:
        print("⚠️  Skipping process job check (no job data)")
        return
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found")
        return
    
    init_firestore()
    firestore_client = get_firestore_client()
    
    # Query process jobs for this drama
    # Note: Firestore requires index for order_by, so we'll query without it first
    query = (
        firestore_client.collection(FIRESTORE_COLLECTION)
        .where("drama_name", "==", drama_name)
        .limit(10)
    )
    
    jobs = list(query.stream())
    
    if jobs:
        print(f"  ✅ Found {len(jobs)} job(s) for drama: {drama_name}")
        
        for job in jobs:
            job_id = job.id
            job_data = job.to_dict() or {}
            
            print(f"\n  Job ID: {job_id}")
            print(f"    status: {job_data.get('status', 'N/A')}")
            print(f"    stage: {job_data.get('stage', 'N/A')}")
            print(f"    type: {job_data.get('type', 'N/A')}")
            print(f"    transfer_completed: {job_data.get('transfer_completed', False)}")
            print(f"    total_files: {job_data.get('total_files', 'N/A')}")
            print(f"    processed_files: {job_data.get('processed_files', 'N/A')}")
            print(f"    failed_files: {job_data.get('failed_files', 'N/A')}")
            print(f"    created_at: {job_data.get('created_at', 'N/A')}")
            
            # Check if this is a process job (stage=2 or type=process)
            stage = job_data.get("stage")
            job_type = job_data.get("type", "").lower()
            
            if stage == 2 or "process" in job_type:
                print(f"    ✅ This is a PROCESS job")
                
                # Check task documents
                tasks_ref = job.reference.collection("tasks")
                tasks = list(tasks_ref.stream())
                
                if tasks:
                    print(f"    ✅ Found {len(tasks)} task document(s)")
                    for task in tasks:
                        task_data = task.to_dict() or {}
                        print(f"      Task {task.id}: status={task_data.get('status', 'N/A')}, "
                              f"progress={task_data.get('progress_count', 0)}/{task_data.get('total_count', 0)}")
                else:
                    print(f"    ⚠️  No task documents found (job may not have started)")
            else:
                print(f"    ℹ️  This is a TRANSFER job (not process)")
    else:
        print(f"  ❌ No jobs found for drama: {drama_name}")
        print(f"     This indicates process job was NOT created")


def check_file_pairing(job_data: dict | None):
    """Check file pairing accuracy."""
    print_section("6. File Pairing Accuracy")
    
    if not job_data:
        print("⚠️  Skipping pairing check (no job data)")
        return
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found")
        return
    
    source_bucket = job_data.get("gcs_source_bucket") or "vigloo_source"
    
    try:
        from app.services.pipeline_discovery_service import discover_file_pairs
        
        print(f"  Discovering file pairs for drama: {drama_name}")
        print(f"  Bucket: {source_bucket}")
        
        pairs = discover_file_pairs(
            drama_name=drama_name,
            source_bucket=source_bucket,
        )
        
        print(f"\n  ✅ Found {len(pairs)} file pair(s)")
        
        if pairs:
            print(f"\n  Sample pairs (first 10):")
            for i, pair in enumerate(pairs[:10], 1):
                print(f"    {i}. EP{pair.episode} | Lang: {pair.language}")
                print(f"       Video: {pair.video_path}")
                print(f"       Subtitle: {pair.subtitle_path}")
            
            if len(pairs) > 10:
                print(f"    ... and {len(pairs) - 10} more")
        else:
            print(f"  ⚠️  No file pairs found")
            print(f"     This may indicate pairing issues")
    
    except Exception as exc:
        print(f"  ❌ Error checking file pairing: {exc}")
        import traceback
        traceback.print_exc()


def check_sharding_status(job_data: dict | None):
    """Check sharding execution status."""
    print_section("7. Sharding Execution Status")
    
    if not job_data:
        print("⚠️  Skipping sharding check (no job data)")
        return
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found")
        return
    
    firestore_client = firestore.Client(project=PROJECT_ID)
    
    # Find process jobs for this drama
    query = (
        firestore_client.collection(FIRESTORE_COLLECTION)
        .where("drama_name", "==", drama_name)
        .where("stage", "==", 2)
        .limit(1)
    )
    
    process_jobs = list(query.stream())
    
    if not process_jobs:
        print(f"  ⚠️  No process jobs found (stage=2)")
        return
    
    process_job = process_jobs[0]
    process_job_id = process_job.id
    process_job_data = process_job.to_dict() or {}
    
    print(f"  Process Job ID: {process_job_id}")
    print(f"  total_files: {process_job_data.get('total_files', 'N/A')}")
    
    # Check task documents
    tasks_ref = process_job.reference.collection("tasks")
    tasks = list(tasks_ref.stream())
    
    if tasks:
        print(f"\n  ✅ Found {len(tasks)} task document(s)")
        
        total_assigned = 0
        total_processed = 0
        total_failed = 0
        
        for task in tasks:
            task_data = task.to_dict() or {}
            task_index = task.id
            status = task_data.get("status", "N/A")
            total_count = task_data.get("total_count", 0)
            progress_count = task_data.get("progress_count", 0)
            success_files = task_data.get("success_files", [])
            failed_files = task_data.get("failed_files", [])
            
            total_assigned += total_count
            total_processed += progress_count
            total_failed += len(failed_files)
            
            print(f"\n    Task {task_index}:")
            print(f"      status: {status}")
            print(f"      assigned: {total_count} files")
            print(f"      processed: {progress_count} files")
            print(f"      succeeded: {len(success_files)} files")
            print(f"      failed: {len(failed_files)} files")
            print(f"      current_file: {task_data.get('current_file', 'N/A')}")
        
        print(f"\n  Summary:")
        print(f"    Total tasks: {len(tasks)}")
        print(f"    Total assigned: {total_assigned} files")
        print(f"    Total processed: {total_processed} files")
        print(f"    Total failed: {total_failed} files")
        
        # Check main job status
        main_processed = process_job_data.get("processed_files", 0)
        main_failed = process_job_data.get("failed_files", 0)
        main_total = process_job_data.get("total_files", 0)
        
        print(f"\n  Main Job Status:")
        print(f"    total_files: {main_total}")
        print(f"    processed_files: {main_processed}")
        print(f"    failed_files: {main_failed}")
        
        if main_total > 0:
            progress_pct = ((main_processed + main_failed) / main_total) * 100
            print(f"    progress: {progress_pct:.1f}%")
    else:
        print(f"  ⚠️  No task documents found")
        print(f"     This indicates sharding was not initialized")


def main():
    """Main diagnostic function."""
    print("=" * 80)
    print("  Auto-Trigger Diagnostic Tool")
    print("=" * 80)
    print(f"\n  Transfer Job ID: {TRANSFER_JOB_ID}")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Region: {REGION}")
    
    # Check transfer job status
    job_data = check_transfer_job_status()
    
    # Check GCS signal file
    signal_exists = check_gcs_signal_file(job_data)
    
    # Check Eventarc trigger
    check_eventarc_trigger()
    
    # Check Relay Service logs
    check_relay_service_logs(job_data)
    
    # Check process jobs
    check_process_jobs(job_data)
    
    # Check file pairing
    check_file_pairing(job_data)
    
    # Check sharding status
    check_sharding_status(job_data)
    
    # Summary
    print_section("Summary & Recommendations")
    
    if not signal_exists:
        print("  ❌ CRITICAL: GCS signal file (_PROCESS_NOW.txt) does not exist")
        print("     → This is likely why Eventarc did not trigger")
        print("     → Action: Check transfer worker logs to see why signal file was not created")
    
    print("\n  Next steps:")
    print("    1. If signal file missing: Check transfer worker logs")
    print("    2. If Eventarc not configured: Verify Eventarc trigger setup")
    print("    3. If Relay Service not triggered: Check Eventarc logs")
    print("    4. If process job not created: Check Relay Service logs")
    print("    5. If pairing failed: Check file structure in GCS")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

