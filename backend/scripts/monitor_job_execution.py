#!/usr/bin/env python3
"""Monitor job execution: Eventarc → Relay Service → Cloud Run Job → Sharding.

This script monitors:
1. Eventarc event capture
2. Relay Service processing
3. Process job creation
4. Task sharding and distribution
5. Concurrent execution (50 containers)
6. Processing speed
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import init_firestore, get_firestore_client
from google.cloud import storage

# Configuration
PROJECT_ID = "fleet-blend-469520-n7"
REGION = "us-central1"
EVENTARC_REGION = "asia-northeast3"
TRANSFER_JOB_ID = "aPUavEyOvn55TRdUwnpY"
FIRESTORE_COLLECTION = "pipeline_jobs"


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
    """Check transfer job status."""
    print_section("1. Transfer Job Status")
    
    init_firestore()
    firestore = get_firestore_client()
    job_ref = firestore.collection(FIRESTORE_COLLECTION).document(TRANSFER_JOB_ID)
    job_snapshot = job_ref.get()
    
    if not job_snapshot.exists:
        print(f"❌ Transfer job {TRANSFER_JOB_ID} does not exist")
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
    
    transfer_completed = job_data.get("transfer_completed", False)
    stage = job_data.get("stage")
    
    if transfer_completed and (stage == 1 or stage is None):
        print(f"\n  ✅ Transfer is completed and ready for processing")
    else:
        print(f"\n  ⚠️  Transfer may not be ready: transfer_completed={transfer_completed}, stage={stage}")
    
    return job_data


def check_gcs_signal_file(job_data: dict | None):
    """Check GCS signal file."""
    print_section("2. GCS Signal File")
    
    if not job_data:
        print("⚠️  Skipping (no job data)")
        return False
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found")
        return False
    
    source_bucket = job_data.get("gcs_source_bucket") or "vigloo_source"
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(source_bucket)
    
    signal_path = f"{drama_name}/_PROCESS_NOW.txt"
    blob = bucket.blob(signal_path)
    
    print(f"  Checking: gs://{source_bucket}/{signal_path}")
    
    if blob.exists():
        blob.reload()
        print(f"  ✅ Signal file exists")
        print(f"     Created: {blob.time_created}")
        print(f"     Updated: {blob.updated}")
        
        # Check if it was created after transfer completion
        updated_at = job_data.get("updated_at")
        if updated_at and blob.time_created:
            if isinstance(updated_at, datetime):
                time_diff = (blob.time_created - updated_at).total_seconds()
                print(f"     Time diff from job update: {time_diff:.1f} seconds")
        
        return True
    else:
        print(f"  ❌ Signal file does NOT exist")
        return False


def check_eventarc_events(job_data: dict | None):
    """Check Eventarc events for this signal file."""
    print_section("3. Eventarc Event Capture")
    
    if not job_data:
        print("⚠️  Skipping (no job data)")
        return
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found")
        return
    
    signal_path = f"{drama_name}/_PROCESS_NOW.txt"
    
    print(f"  Checking Eventarc events for: {signal_path}")
    print(f"  Note: Eventarc events may take a few seconds to appear in logs")
    
    try:
        import subprocess
        
        # Query Cloud Logging for Eventarc events
        # Eventarc events appear in Cloud Logging with specific resource types
        filter_str = (
            f'resource.type="eventarc_trigger" '
            f'AND resource.labels.trigger_name="drama-processor-trigger" '
            f'AND resource.labels.location="{EVENTARC_REGION}" '
            f'AND jsonPayload.event.data.name=~"{signal_path}"'
        )
        
        result = subprocess.run(
            [
                "gcloud", "logging", "read",
                filter_str,
                "--limit", "5",
                "--format", "table(timestamp,jsonPayload.event.data.name,jsonPayload.event.data.bucket)",
                "--project", PROJECT_ID,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"\n  ✅ Found Eventarc events:")
            print(result.stdout)
        else:
            print(f"\n  ⚠️  No Eventarc events found in logs yet")
            print(f"     This may be normal if:")
            print(f"     - Event was just created (< 30 seconds ago)")
            print(f"     - Logs haven't been indexed yet")
            print(f"     - Eventarc trigger is not configured correctly")
    
    except Exception as exc:
        print(f"  ⚠️  Error checking Eventarc events: {exc}")


def check_relay_service_logs(job_data: dict | None):
    """Check Relay Service logs."""
    print_section("4. Relay Service Processing")
    
    if not job_data:
        print("⚠️  Skipping (no job data)")
        return
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found")
        return
    
    print(f"  Checking Relay Service logs for drama: {drama_name}")
    
    try:
        import subprocess
        
        # Query recent logs (last 10 minutes)
        filter_str = (
            f'resource.type="cloud_run_revision" '
            f'AND resource.labels.service_name="drama-processor-relay-service" '
            f'AND textPayload=~"{drama_name}"'
        )
        
        result = subprocess.run(
            [
                "gcloud", "logging", "read",
                filter_str,
                "--limit", "20",
                "--format", "table(timestamp,textPayload)",
                "--project", PROJECT_ID,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"\n  ✅ Found Relay Service logs:")
            print(result.stdout)
            
            # Check for key log messages
            output = result.stdout.lower()
            if "接收到 eventarc 事件" in output or "接收到 eventarc" in output:
                print(f"\n  ✅ Event received by Relay Service")
            if "匹配到 pipeline job" in output or "找到 ready job" in output:
                print(f"  ✅ Job found and matched")
            if "已触发 cloud run job" in output or "triggered" in output:
                print(f"  ✅ Cloud Run Job triggered")
        else:
            print(f"\n  ⚠️  No Relay Service logs found")
            print(f"     This may indicate:")
            print(f"     - Eventarc event not received yet")
            print(f"     - Relay Service not processing the event")
    
    except Exception as exc:
        print(f"  ⚠️  Error checking logs: {exc}")


def check_process_job(job_data: dict | None):
    """Check if process job was created."""
    print_section("5. Process Job Creation")
    
    if not job_data:
        print("⚠️  Skipping (no job data)")
        return None
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found")
        return None
    
    init_firestore()
    firestore = get_firestore_client()
    
    # Find process jobs for this drama (stage=2 or type=process)
    query = (
        firestore.collection(FIRESTORE_COLLECTION)
        .where("drama_name", "==", drama_name)
        .limit(10)
    )
    
    jobs = list(query.stream())
    process_jobs = []
    
    for job in jobs:
        job_data_check = job.to_dict() or {}
        stage = job_data_check.get("stage")
        job_type = job_data_check.get("type", "").lower()
        
        if stage == 2 or "process" in job_type:
            process_jobs.append((job.id, job_data_check))
    
    if process_jobs:
        # Find the most recent one (likely for this transfer)
        process_jobs.sort(key=lambda x: x[1].get("created_at", datetime.min), reverse=True)
        process_job_id, process_job_data = process_jobs[0]
        
        print(f"  ✅ Found process job: {process_job_id}")
        print(f"\n  Job Details:")
        print(f"    status: {process_job_data.get('status', 'N/A')}")
        print(f"    stage: {process_job_data.get('stage', 'N/A')}")
        print(f"    total_files: {process_job_data.get('total_files', 'N/A')}")
        print(f"    processed_files: {process_job_data.get('processed_files', 0)}")
        print(f"    failed_files: {process_job_data.get('failed_files', 0)}")
        print(f"    created_at: {process_job_data.get('created_at', 'N/A')}")
        print(f"    updated_at: {process_job_data.get('updated_at', 'N/A')}")
        
        return process_job_id, process_job_data
    else:
        print(f"  ⚠️  No process jobs found for drama: {drama_name}")
        print(f"     This may indicate:")
        print(f"     - Process job not created yet")
        print(f"     - Relay Service not triggered")
        return None, None


def check_task_sharding(process_job_id: str | None, process_job_data: dict | None):
    """Check task sharding and distribution."""
    print_section("6. Task Sharding & Distribution")
    
    if not process_job_id or not process_job_data:
        print("⚠️  Skipping (no process job)")
        return
    
    total_files = process_job_data.get("total_files")
    if total_files is None:
        print("  ⚠️  total_files not set yet")
        return
    
    print(f"  Total files: {total_files}")
    
    # Calculate expected task_count
    import math
    if total_files <= 100:
        expected_task_count = total_files
    else:
        expected_task_count = min(math.ceil(total_files / 3), 100)
    
    print(f"  Expected task_count: {expected_task_count}")
    print(f"  Expected files per task: {total_files / expected_task_count:.2f}")
    
    # Check actual task documents
    init_firestore()
    firestore = get_firestore_client()
    job_ref = firestore.collection(FIRESTORE_COLLECTION).document(process_job_id)
    tasks_ref = job_ref.collection("tasks")
    tasks = list(tasks_ref.stream())
    
    if tasks:
        print(f"\n  ✅ Found {len(tasks)} task document(s)")
        
        total_assigned = 0
        total_processed = 0
        total_succeeded = 0
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
            total_succeeded += len(success_files)
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
        print(f"    Expected tasks: {expected_task_count}")
        if len(tasks) == expected_task_count:
            print(f"    ✅ Task count matches expected")
        else:
            print(f"    ⚠️  Task count mismatch: {len(tasks)} vs {expected_task_count}")
        
        print(f"    Total assigned: {total_assigned} files")
        print(f"    Total processed: {total_processed} files")
        print(f"    Total succeeded: {total_succeeded} files")
        print(f"    Total failed: {total_failed} files")
        
        if total_assigned > 0:
            progress_pct = (total_processed / total_assigned) * 100
            print(f"    Progress: {progress_pct:.1f}%")
    else:
        print(f"  ⚠️  No task documents found")
        print(f"     This may indicate:")
        print(f"     - Tasks not initialized yet")
        print(f"     - Cloud Run Job not started")


def check_cloud_run_job_execution(process_job_id: str | None):
    """Check Cloud Run Job execution and concurrency."""
    print_section("7. Cloud Run Job Execution & Concurrency")
    
    if not process_job_id:
        print("⚠️  Skipping (no process job)")
        return
    
    try:
        import subprocess
        
        # List recent executions
        result = subprocess.run(
            [
                "gcloud", "run", "jobs", "executions", "list",
                "--job", "drama-processor-job",
                "--region", REGION,
                "--project", PROJECT_ID,
                "--limit", "5",
                "--format", "table(name,status.completionTime,status.succeededCount,status.failedCount,status.runningCount,status.conditions[0].type,status.conditions[0].status)",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"  Recent executions:")
            print(result.stdout)
            
            # Get the latest execution details
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Has header + at least one execution
                latest_execution_name = lines[1].split()[0] if lines[1].split() else None
                
                if latest_execution_name:
                    print(f"\n  Checking latest execution: {latest_execution_name}")
                    
                    # Get execution details
                    detail_result = subprocess.run(
                        [
                            "gcloud", "run", "jobs", "executions", "describe",
                            latest_execution_name,
                            "--region", REGION,
                            "--project", PROJECT_ID,
                            "--format", "yaml(spec.taskCount,status.succeededCount,status.failedCount,status.runningCount,status.conditions)",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    
                    if detail_result.returncode == 0:
                        print(f"\n  Execution details:")
                        print(detail_result.stdout)
                        
                        # Check task_count
                        if "taskCount:" in detail_result.stdout:
                            import re
                            match = re.search(r'taskCount:\s*(\d+)', detail_result.stdout)
                            if match:
                                task_count = int(match.group(1))
                                print(f"\n  ✅ Task count: {task_count}")
                                
                                if task_count == 50:
                                    print(f"     ✅ Maximum parallelism (50) reached")
                                elif task_count < 50:
                                    print(f"     ℹ️  Using {task_count} tasks (less than max 50)")
        else:
            print(f"  ⚠️  No executions found or error")
            print(result.stderr)
    
    except Exception as exc:
        print(f"  ⚠️  Error checking executions: {exc}")


def check_processing_speed(process_job_data: dict | None):
    """Check processing speed."""
    print_section("8. Processing Speed Analysis")
    
    if not process_job_data:
        print("⚠️  Skipping (no process job)")
        return
    
    total_files = process_job_data.get("total_files")
    processed_files = process_job_data.get("processed_files", 0)
    failed_files = process_job_data.get("failed_files", 0)
    created_at = process_job_data.get("created_at")
    updated_at = process_job_data.get("updated_at")
    
    if not total_files or total_files == 0:
        print("  ⚠️  total_files not set or 0")
        return
    
    print(f"  Total files: {total_files}")
    print(f"  Processed: {processed_files}")
    print(f"  Failed: {failed_files}")
    print(f"  Remaining: {total_files - processed_files - failed_files}")
    
    if created_at and updated_at:
        if isinstance(created_at, datetime) and isinstance(updated_at, datetime):
            elapsed = (updated_at - created_at).total_seconds()
            elapsed_minutes = elapsed / 60
            
            print(f"\n  Time Analysis:")
            print(f"    Created: {created_at}")
            print(f"    Last updated: {updated_at}")
            print(f"    Elapsed: {elapsed_minutes:.1f} minutes ({elapsed:.0f} seconds)")
            
            if processed_files > 0:
                files_per_minute = processed_files / elapsed_minutes if elapsed_minutes > 0 else 0
                estimated_total_minutes = total_files / files_per_minute if files_per_minute > 0 else 0
                remaining_files = total_files - processed_files - failed_files
                estimated_remaining_minutes = remaining_files / files_per_minute if files_per_minute > 0 else 0
                
                print(f"\n  Speed Metrics:")
                print(f"    Files per minute: {files_per_minute:.2f}")
                print(f"    Estimated total time: {estimated_total_minutes:.1f} minutes")
                print(f"    Estimated remaining time: {estimated_remaining_minutes:.1f} minutes")
                
                # Compare with expected speed
                # With 50 concurrent tasks, each processing ~3 files, and ~20-25 min per file
                # Expected: 50 tasks * (60 min / 22.5 min per file) = ~133 files/hour = ~2.2 files/min
                expected_min = 2.0  # Conservative estimate
                expected_max = 3.0  # Optimistic estimate
                
                if files_per_minute >= expected_min:
                    print(f"    ✅ Speed is within expected range ({expected_min}-{expected_max} files/min)")
                else:
                    print(f"    ⚠️  Speed is below expected range ({expected_min}-{expected_max} files/min)")
                    print(f"       This may indicate:")
                    print(f"       - Not all tasks are running concurrently")
                    print(f"       - Tasks are processing slower than expected")
                    print(f"       - Resource constraints")


def main():
    """Main monitoring function."""
    print("=" * 80)
    print("  Job Execution Monitor")
    print("=" * 80)
    print(f"\n  Transfer Job ID: {TRANSFER_JOB_ID}")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Region: {REGION}")
    print(f"  Eventarc Region: {EVENTARC_REGION}")
    
    # Step 1: Check transfer job
    job_data = check_transfer_job_status()
    
    # Step 2: Check signal file
    signal_exists = check_gcs_signal_file(job_data)
    
    # Step 3: Check Eventarc events
    check_eventarc_events(job_data)
    
    # Step 4: Check Relay Service logs
    check_relay_service_logs(job_data)
    
    # Step 5: Check process job
    process_job_id, process_job_data = check_process_job(job_data)
    
    # Step 6: Check task sharding
    check_task_sharding(process_job_id, process_job_data)
    
    # Step 7: Check Cloud Run Job execution
    check_cloud_run_job_execution(process_job_id)
    
    # Step 8: Check processing speed
    check_processing_speed(process_job_data)
    
    # Summary
    print_section("Summary & Recommendations")
    
    print("  Key Observations:")
    
    if not signal_exists:
        print("  ❌ Signal file not found - Eventarc cannot trigger")
    
    if not process_job_id:
        print("  ⚠️  Process job not created - Check Relay Service logs")
    
    if process_job_data:
        total_files = process_job_data.get("total_files", 0)
        if total_files == 0:
            print("  ⚠️  total_files is 0 - File pairing may have failed")
        else:
            print(f"  ✅ total_files set correctly: {total_files}")
    
    print("\n  Next steps:")
    print("    1. Monitor GitHub Actions deployment status")
    print("    2. Check Relay Service logs for Eventarc events")
    print("    3. Verify Cloud Run Job executions")
    print("    4. Monitor Firestore for task document updates")
    print("    5. Check processing speed and concurrency")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()


