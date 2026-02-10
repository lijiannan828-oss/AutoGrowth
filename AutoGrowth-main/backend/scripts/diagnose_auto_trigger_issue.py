#!/usr/bin/env python3
"""Diagnose auto-trigger issue for a specific drama."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.firestore import init_firestore, get_firestore_client
from google.cloud import storage

DRAMA_NAME = "KR071P01S01_타임 리프 조선"
PROJECT_ID = "fleet-blend-469520-n7"
REGION = "us-central1"
EVENTARC_REGION = "asia-northeast3"
SOURCE_BUCKET = "vigloo_source"


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def check_transfer_job():
    """Check transfer job status."""
    print_section("1. Transfer Job Status")
    
    init_firestore()
    firestore = get_firestore_client()
    
    # Find transfer job for this drama
    from google.cloud.firestore_v1 import Query
    query = (
        firestore.collection("pipeline_jobs")
        .where("drama_name", "==", DRAMA_NAME)
        .where("stage", "==", 1)
        .order_by("updated_at", direction=Query.DESCENDING)
        .limit(5)
    )
    
    jobs = list(query.stream())
    
    if not jobs:
        print(f"❌ 未找到传输任务 (drama_name={DRAMA_NAME}, stage=1)")
        return None
    
    job = jobs[0]
    job_data = job.to_dict() or {}
    
    print(f"✅ 找到传输任务: {job.id}")
    print(f"\n  Job Details:")
    print(f"    drama_name: {job_data.get('drama_name', 'N/A')}")
    print(f"    status: {job_data.get('status', 'N/A')}")
    print(f"    stage: {job_data.get('stage', 'N/A')}")
    print(f"    transfer_completed: {job_data.get('transfer_completed', False)}")
    print(f"    created_at: {job_data.get('created_at', 'N/A')}")
    print(f"    updated_at: {job_data.get('updated_at', 'N/A')}")
    
    transfer_completed = job_data.get("transfer_completed", False)
    status = job_data.get("status", "")
    
    if transfer_completed and status in ["COMPLETE", "SUCCEEDED"]:
        print(f"\n  ✅ 传输已完成，应该触发压制任务")
    else:
        print(f"\n  ⚠️  传输可能未完成: transfer_completed={transfer_completed}, status={status}")
    
    return job.id, job_data


def check_gcs_signal_file(job_data):
    """Check GCS signal file."""
    print_section("2. GCS Signal File")
    
    if not job_data:
        print("⚠️  Skipping (no job data)")
        return False
    
    signal_path = f"{DRAMA_NAME}/_PROCESS_NOW.txt"
    
    print(f"  Checking: gs://{SOURCE_BUCKET}/{signal_path}")
    
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(SOURCE_BUCKET)
    blob = bucket.blob(signal_path)
    
    if blob.exists():
        blob.reload()
        print(f"  ✅ Signal file exists")
        print(f"     Created: {blob.time_created}")
        print(f"     Updated: {blob.updated}")
        
        # Check creation time vs job update time
        updated_at = job_data.get("updated_at")
        if updated_at and blob.time_created:
            if isinstance(updated_at, datetime):
                time_diff = (blob.time_created - updated_at).total_seconds()
                print(f"     Time diff from job update: {time_diff:.1f} seconds")
        
        return True
    else:
        print(f"  ❌ Signal file does NOT exist")
        print(f"     这是问题所在！信号文件未创建")
        return False


def check_eventarc_events():
    """Check Eventarc events."""
    print_section("3. Eventarc Events")
    
    signal_path = f"{DRAMA_NAME}/_PROCESS_NOW.txt"
    
    print(f"  Checking Eventarc events for: {signal_path}")
    print(f"  Note: Events may take 30-60 seconds to appear in logs")
    
    import subprocess
    
    try:
        # Query Cloud Logging for Eventarc events
        filter_str = (
            f'resource.type="eventarc_trigger" '
            f'AND resource.labels.trigger_name="drama-processor-trigger" '
            f'AND resource.labels.location="{EVENTARC_REGION}" '
            f'AND timestamp>="{(datetime.utcnow() - timedelta(hours=1)).isoformat()}Z"'
        )
        
        result = subprocess.run(
            [
                "gcloud", "logging", "read",
                filter_str,
                "--limit", "20",
                "--format", "json",
                "--project", PROJECT_ID,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        
        if result.returncode == 0:
            import json
            events = json.loads(result.stdout)
            
            if events:
                print(f"\n  ✅ Found {len(events)} Eventarc event(s)")
                for i, event in enumerate(events[:5], 1):
                    timestamp = event.get("timestamp", "N/A")
                    payload = event.get("jsonPayload", {})
                    data = payload.get("data", {})
                    object_name = data.get("name", "N/A")
                    
                    print(f"\n  Event {i}:")
                    print(f"    Timestamp: {timestamp}")
                    print(f"    Object: {object_name}")
                    
                    if DRAMA_NAME in object_name:
                        print(f"    ✅ Matches our drama!")
            else:
                print(f"\n  ⚠️  No Eventarc events found")
                print(f"     可能原因:")
                print(f"     - 事件还未触发（需要等待30-60秒）")
                print(f"     - Eventarc 触发器配置问题")
        else:
            print(f"\n  ⚠️  Error querying events: {result.stderr}")
    
    except Exception as exc:
        print(f"  ⚠️  Error checking Eventarc events: {exc}")


def check_relay_service_logs():
    """Check Relay Service logs."""
    print_section("4. Relay Service Logs")
    
    print(f"  Checking Relay Service logs for drama: {DRAMA_NAME}")
    
    import subprocess
    
    try:
        # Query recent logs (last hour)
        filter_str = (
            f'resource.type="cloud_run_revision" '
            f'AND resource.labels.service_name="drama-processor-relay-service" '
            f'AND timestamp>="{(datetime.utcnow() - timedelta(hours=1)).isoformat()}Z"'
        )
        
        result = subprocess.run(
            [
                "gcloud", "logging", "read",
                filter_str,
                "--limit", "100",
                "--format", "json",
                "--project", PROJECT_ID,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        
        if result.returncode == 0:
            import json
            logs = json.loads(result.stdout)
            
            if not logs:
                print(f"\n  ⚠️  No Relay Service logs found")
                return
            
            print(f"\n  ✅ Found {len(logs)} log entries")
            
            # Filter relevant logs
            relevant_logs = []
            for log in logs:
                payload = log.get("textPayload", "") or str(log.get("jsonPayload", {}))
                if DRAMA_NAME in payload or "_PROCESS_NOW" in payload or "接收到" in payload or "匹配到" in payload or "已触发" in payload:
                    relevant_logs.append(log)
            
            if relevant_logs:
                print(f"\n  ✅ Found {len(relevant_logs)} relevant log entries:")
                for log in relevant_logs[:10]:
                    timestamp = log.get("timestamp", "N/A")
                    payload = log.get("textPayload", "") or str(log.get("jsonPayload", {}))
                    print(f"\n    [{timestamp}] {payload[:300]}")
            else:
                print(f"\n  ⚠️  No relevant logs found for this drama")
                print(f"     可能原因:")
                print(f"     - Relay Service 未接收到事件")
                print(f"     - 事件被过滤掉了（非 _PROCESS_NOW.txt）")
                print(f"     - 日志还未被索引")
                
                # Show recent logs anyway
                print(f"\n  Recent logs (last 5):")
                for log in logs[:5]:
                    timestamp = log.get("timestamp", "N/A")
                    payload = log.get("textPayload", "") or str(log.get("jsonPayload", {}))
                    print(f"    [{timestamp}] {payload[:200]}")
        else:
            print(f"\n  ⚠️  Error querying logs: {result.stderr}")
    
    except Exception as exc:
        print(f"  ⚠️  Error checking logs: {exc}")


def check_process_job():
    """Check if process job was created."""
    print_section("5. Process Job Status")
    
    init_firestore()
    firestore = get_firestore_client()
    
    # Find process jobs for this drama
    query = (
        firestore.collection("pipeline_jobs")
        .where("drama_name", "==", DRAMA_NAME)
        .limit(10)
    )
    
    jobs = list(query.stream())
    process_jobs = []
    
    for job in jobs:
        job_data = job.to_dict() or {}
        stage = job_data.get("stage")
        
        if stage == 2:  # Process job
            process_jobs.append((job.id, job_data))
    
    if process_jobs:
        print(f"  ✅ Found {len(process_jobs)} process job(s)")
        for job_id, job_data in process_jobs:
            print(f"\n  Job ID: {job_id}")
            print(f"    status: {job_data.get('status', 'N/A')}")
            print(f"    total_files: {job_data.get('total_files', 'N/A')}")
            print(f"    created_at: {job_data.get('created_at', 'N/A')}")
    else:
        print(f"  ❌ No process jobs found")
        print(f"     这是问题所在！压制任务未创建")
    
    return process_jobs


def check_eventarc_trigger():
    """Check Eventarc trigger configuration."""
    print_section("6. Eventarc Trigger Configuration")
    
    import subprocess
    
    try:
        result = subprocess.run(
            [
                "gcloud", "eventarc", "triggers", "describe",
                "drama-processor-trigger",
                "--location", EVENTARC_REGION,
                "--project", PROJECT_ID,
                "--format", "yaml(destination.cloudRun.path,destination.cloudRun.service,destination.cloudRun.region,eventFilters)",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        
        if result.returncode == 0:
            print(f"  ✅ Trigger configuration:")
            print(result.stdout)
        else:
            print(f"  ❌ Error getting trigger config: {result.stderr}")
    
    except Exception as exc:
        print(f"  ⚠️  Error checking trigger: {exc}")


def main():
    """Main diagnostic function."""
    print("=" * 80)
    print("  Auto-Trigger Diagnostic")
    print("=" * 80)
    print(f"\n  Drama Name: {DRAMA_NAME}")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Source Bucket: {SOURCE_BUCKET}")
    
    # Step 1: Check transfer job
    transfer_job_info = check_transfer_job()
    transfer_job_id = transfer_job_info[0] if transfer_job_info else None
    transfer_job_data = transfer_job_info[1] if transfer_job_info else None
    
    # Step 2: Check signal file
    signal_exists = check_gcs_signal_file(transfer_job_data)
    
    # Step 3: Check Eventarc events
    check_eventarc_events()
    
    # Step 4: Check Relay Service logs
    check_relay_service_logs()
    
    # Step 5: Check process job
    process_jobs = check_process_job()
    
    # Step 6: Check Eventarc trigger
    check_eventarc_trigger()
    
    # Summary
    print_section("Diagnosis Summary")
    
    print("  Key Findings:")
    
    if not transfer_job_id:
        print("  ❌ Transfer job not found")
    
    if not signal_exists:
        print("  ❌ Signal file not found - This is likely the root cause!")
        print("     The transfer job may not have created the _PROCESS_NOW.txt file")
    
    if not process_jobs:
        print("  ❌ Process job not created")
        print("     This confirms the auto-trigger failed")
    
    print("\n  Next Steps:")
    if not signal_exists:
        print("  1. Check why the signal file was not created")
        print("  2. Verify transfer job completion logic")
        print("  3. Manually create signal file if needed")
    else:
        print("  1. Check Eventarc trigger configuration")
        print("  2. Check Relay Service logs for errors")
        print("  3. Verify Relay Service can find the ready job")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

