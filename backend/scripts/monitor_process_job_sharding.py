#!/usr/bin/env python3
"""Monitor process job sharding: Firestore, Cloud Run Jobs, and execution details."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.firestore import init_firestore, get_firestore_client
from app.services.pipeline_discovery_service import discover_file_pairs

PROCESS_JOB_ID = "akln3K9gWpb6dJdJuWbE"
PROJECT_ID = "fleet-blend-469520-n7"
REGION = "us-central1"
JOB_NAME = "drama-processor-job"


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


def check_firestore_job():
    """Check Firestore job document."""
    print_section("1. Firestore Job Document")
    
    init_firestore()
    firestore = get_firestore_client()
    job_ref = firestore.collection("pipeline_jobs").document(PROCESS_JOB_ID)
    job_snapshot = job_ref.get()
    
    if not job_snapshot.exists:
        print(f"❌ Job {PROCESS_JOB_ID} does not exist in Firestore")
        return None
    
    job_data = job_snapshot.to_dict() or {}
    
    print(f"✅ Job found: {PROCESS_JOB_ID}")
    print(f"\n  Job Details:")
    print(f"    drama_name: {job_data.get('drama_name', 'N/A')}")
    print(f"    status: {job_data.get('status', 'N/A')}")
    print(f"    stage: {job_data.get('stage', 'N/A')}")
    print(f"    type: {job_data.get('type', 'N/A')}")
    print(f"    total_files: {job_data.get('total_files', 'N/A')}")
    print(f"    processed_files: {job_data.get('processed_files', 0)}")
    print(f"    failed_files: {job_data.get('failed_files', 0)}")
    print(f"    created_at: {job_data.get('created_at', 'N/A')}")
    print(f"    updated_at: {job_data.get('updated_at', 'N/A')}")
    
    return job_data


def check_file_pairing(job_data):
    """Check file pairing discovery."""
    print_section("2. File Pairing Discovery")
    
    if not job_data:
        print("⚠️  Skipping (no job data)")
        return None
    
    drama_name = job_data.get("drama_name", "").strip()
    if not drama_name:
        print("❌ drama_name not found")
        return None
    
    source_bucket = job_data.get("gcs_source_bucket") or "vigloo_source"
    
    print(f"  Drama Name: {drama_name}")
    print(f"  Source Bucket: {source_bucket}")
    print(f"  Discovering file pairs...")
    
    try:
        pairs = discover_file_pairs(
            drama_name=drama_name,
            source_bucket=source_bucket,
        )
        total_files = len(pairs)
        
        print(f"\n  ✅ Found {total_files} file pairs")
        
        # Analyze video formats
        video_formats = {}
        for pair in pairs:
            ext = Path(pair.video_path).suffix.lower()
            video_formats[ext] = video_formats.get(ext, 0) + 1
        
        print(f"\n  Video Format Distribution:")
        for ext, count in sorted(video_formats.items(), key=lambda x: -x[1]):
            print(f"    {ext}: {count} files")
        
        # Show first few pairs
        print(f"\n  First 5 pairs:")
        for i, pair in enumerate(pairs[:5], 1):
            episode_str = str(pair.episode).zfill(3) if isinstance(pair.episode, int) else str(pair.episode)
            print(f"    {i}. EP{episode_str} | {pair.language} | {Path(pair.video_path).name}")
        
        return total_files, pairs
    
    except Exception as exc:
        print(f"  ❌ Error discovering file pairs: {exc}")
        import traceback
        traceback.print_exc()
        return None, None


def check_task_sharding(job_data, total_files):
    """Check task sharding logic."""
    print_section("3. Task Sharding Logic")
    
    if not job_data:
        print("⚠️  Skipping (no job data)")
        return
    
    firestore_total = job_data.get("total_files")
    
    print(f"  Firestore total_files: {firestore_total}")
    print(f"  Discovered total_files: {total_files}")
    
    if firestore_total is None:
        print("  ⚠️  total_files not set in Firestore yet")
        return
    
    if firestore_total != total_files:
        print(f"  ⚠️  Mismatch: Firestore={firestore_total}, Discovery={total_files}")
    
    # Calculate expected task_count
    import math
    if firestore_total <= 100:
        expected_task_count = firestore_total
        files_per_task = 1
    else:
        expected_task_count = min(math.ceil(firestore_total / 3), 100)
        files_per_task = firestore_total / expected_task_count
    
    print(f"\n  Expected Sharding:")
    print(f"    total_files: {firestore_total}")
    print(f"    expected_task_count: {expected_task_count}")
    print(f"    expected_files_per_task: {files_per_task:.2f}")
    print(f"    sharding formula: min(ceil({firestore_total} / 3), 100) = {expected_task_count}")
    
    return expected_task_count


def check_firestore_tasks(job_data):
    """Check Firestore task documents."""
    print_section("4. Firestore Task Documents")
    
    if not job_data:
        print("⚠️  Skipping (no job data)")
        return []
    
    init_firestore()
    firestore = get_firestore_client()
    job_ref = firestore.collection("pipeline_jobs").document(PROCESS_JOB_ID)
    tasks_ref = job_ref.collection("tasks")
    tasks = list(tasks_ref.stream())
    
    if not tasks:
        print("  ⚠️  No task documents found")
        print("     This may indicate:")
        print("     - Tasks not initialized yet")
        print("     - Cloud Run Job not started")
        return []
    
    print(f"  ✅ Found {len(tasks)} task document(s)")
    
    task_list = []
    total_assigned = 0
    total_processed = 0
    total_succeeded = 0
    total_failed = 0
    
    for task in tasks:
        task_data = task.to_dict() or {}
        task_index = int(task.id) if task.id.isdigit() else task.id
        status = task_data.get("status", "N/A")
        total_count = task_data.get("total_count", 0)
        progress_count = task_data.get("progress_count", 0)
        success_files = task_data.get("success_files", [])
        failed_files = task_data.get("failed_files", [])
        current_file = task_data.get("current_file", "N/A")
        created_at = task_data.get("created_at")
        updated_at = task_data.get("updated_at")
        
        total_assigned += total_count
        total_processed += progress_count
        total_succeeded += len(success_files)
        total_failed += len(failed_files)
        
        task_info = {
            "index": task_index,
            "status": status,
            "total_count": total_count,
            "progress_count": progress_count,
            "success_count": len(success_files),
            "failed_count": len(failed_files),
            "current_file": current_file,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        task_list.append(task_info)
    
    # Sort by task index
    task_list.sort(key=lambda x: x["index"] if isinstance(x["index"], int) else 999)
    
    print(f"\n  Task Summary:")
    print(f"    Total tasks: {len(tasks)}")
    print(f"    Total assigned: {total_assigned} files")
    print(f"    Total processed: {total_processed} files")
    print(f"    Total succeeded: {total_succeeded} files")
    print(f"    Total failed: {total_failed} files")
    
    if total_assigned > 0:
        progress_pct = (total_processed / total_assigned) * 100
        print(f"    Progress: {progress_pct:.1f}%")
    
    print(f"\n  Individual Task Details:")
    for task_info in task_list:
        print(f"\n    Task {task_info['index']}:")
        print(f"      status: {task_info['status']}")
        print(f"      assigned: {task_info['total_count']} files")
        print(f"      processed: {task_info['progress_count']} files")
        print(f"      succeeded: {task_info['success_count']} files")
        print(f"      failed: {task_info['failed_count']} files")
        print(f"      current_file: {task_info['current_file']}")
        if task_info['created_at']:
            print(f"      created_at: {task_info['created_at']}")
        if task_info['updated_at']:
            print(f"      updated_at: {task_info['updated_at']}")
    
    return task_list


def check_cloud_run_execution():
    """Check Cloud Run Job execution."""
    print_section("5. Cloud Run Job Execution")
    
    import subprocess
    
    try:
        # Get latest execution for this job
        result = subprocess.run(
            [
                "gcloud", "run", "jobs", "executions", "list",
                "--job", JOB_NAME,
                "--region", REGION,
                "--project", PROJECT_ID,
                "--limit", "10",
                "--format", "json",
                "--sort-by", "~status.startTime",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        
        if result.returncode != 0:
            print(f"  ❌ Error listing executions: {result.stderr}")
            return None
        
        import json
        executions = json.loads(result.stdout)
        
        if not executions:
            print("  ⚠️  No executions found")
            return None
        
        # Find execution that matches our job (by checking environment variables or timing)
        # For now, use the latest execution
        latest_execution = executions[0]
        execution_full_name = latest_execution.get("name", "")
        # Extract execution name: projects/.../locations/.../executions/EXECUTION_NAME
        execution_name = execution_full_name.split("/")[-1] if execution_full_name else None
        
        print(f"  ✅ Found {len(executions)} execution(s)")
        print(f"  Latest execution: {execution_name}")
        
        # Get detailed execution info
        detail_result = subprocess.run(
            [
                "gcloud", "run", "jobs", "executions", "describe",
                execution_name,
                "--region", REGION,
                "--project", PROJECT_ID,
                "--format", "json",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        
        if detail_result.returncode != 0:
            print(f"  ❌ Error getting execution details: {detail_result.stderr}")
            return None
        
        execution_data = json.loads(detail_result.stdout)
        
        spec = execution_data.get("spec", {})
        status = execution_data.get("status", {})
        
        task_count = spec.get("taskCount", 0)
        parallelism = spec.get("parallelism", 0)
        task_timeout = spec.get("taskTimeoutSeconds", 0)
        
        succeeded_count = status.get("succeededCount", 0)
        failed_count = status.get("failedCount", 0)
        running_count = status.get("runningCount", 0)
        start_time = status.get("startTime", "")
        completion_time = status.get("completionTime", "")
        
        print(f"\n  Execution Configuration:")
        print(f"    task_count: {task_count}")
        print(f"    parallelism: {parallelism}")
        print(f"    task_timeout: {task_timeout}s ({task_timeout/3600:.1f}h)")
        
        print(f"\n  Execution Status:")
        print(f"    start_time: {start_time}")
        print(f"    completion_time: {completion_time}")
        print(f"    succeeded_count: {succeeded_count}")
        print(f"    failed_count: {failed_count}")
        print(f"    running_count: {running_count}")
        
        # Check conditions
        conditions = status.get("conditions", [])
        print(f"\n  Conditions:")
        for cond in conditions:
            cond_type = cond.get("type", "N/A")
            cond_status = cond.get("status", "N/A")
            cond_message = cond.get("message", "")
            print(f"    {cond_type}: {cond_status}")
            if cond_message:
                print(f"      {cond_message[:100]}")
        
        return {
            "execution_name": execution_name,
            "task_count": task_count,
            "parallelism": parallelism,
            "succeeded_count": succeeded_count,
            "failed_count": failed_count,
            "running_count": running_count,
            "start_time": start_time,
            "completion_time": completion_time,
        }
    
    except Exception as exc:
        print(f"  ❌ Error checking execution: {exc}")
        import traceback
        traceback.print_exc()
        return None


def check_task_logs(execution_info):
    """Check individual task logs."""
    print_section("6. Individual Task Logs & Timing")
    
    if not execution_info:
        print("⚠️  Skipping (no execution info)")
        return
    
    execution_name = execution_info.get("execution_name")
    task_count = execution_info.get("task_count", 0)
    
    if not execution_name or task_count == 0:
        print("⚠️  No execution or task_count is 0")
        return
    
    print(f"  Execution: {execution_name}")
    print(f"  Task Count: {task_count}")
    print(f"\n  Fetching logs for individual tasks...")
    
    import subprocess
    
    # Query logs for this execution
    filter_str = (
        f'resource.type="cloud_run_job" '
        f'resource.labels.job_name="{JOB_NAME}" '
        f'resource.labels.location="{REGION}" '
        f'labels."run.googleapis.com/execution_name"="{execution_name}"'
    )
    
    try:
        result = subprocess.run(
            [
                "gcloud", "logging", "read",
                filter_str,
                "--limit", "500",
                "--format", "json",
                "--project", PROJECT_ID,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        
        if result.returncode != 0:
            print(f"  ❌ Error fetching logs: {result.stderr}")
            return
        
        import json
        logs = json.loads(result.stdout)
        
        if not logs:
            print("  ⚠️  No logs found")
            return
        
        print(f"  ✅ Found {len(logs)} log entries")
        
        # Group logs by task
        task_logs = {}
        for log_entry in logs:
            labels = log_entry.get("labels", {})
            task_index = labels.get("run.googleapis.com/task_index", "unknown")
            
            if task_index not in task_logs:
                task_logs[task_index] = []
            
            timestamp = log_entry.get("timestamp", "")
            payload = log_entry.get("textPayload", "") or str(log_entry.get("jsonPayload", {}))
            
            task_logs[task_index].append({
                "timestamp": timestamp,
                "payload": payload,
            })
        
        print(f"\n  Task Log Summary:")
        print(f"    Found logs for {len(task_logs)} task(s)")
        
        # Show key events for each task
        for task_index in sorted(task_logs.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            logs_for_task = task_logs[task_index]
            logs_for_task.sort(key=lambda x: x["timestamp"])
            
            print(f"\n    Task {task_index} ({len(logs_for_task)} log entries):")
            
            # Find key events
            start_time = None
            end_time = None
            key_messages = []
            
            for log in logs_for_task:
                payload = log["payload"].lower()
                timestamp = log["timestamp"]
                
                if not start_time:
                    start_time = timestamp
                
                end_time = timestamp
                
                # Look for key messages
                if any(keyword in payload for keyword in ["task", "claimed", "processing", "completed", "success", "failed"]):
                    if len(key_messages) < 5:  # Limit to first 5 key messages
                        key_messages.append(f"      [{timestamp}] {log['payload'][:150]}")
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    duration = (end_dt - start_dt).total_seconds()
                    print(f"      Duration: {duration:.1f}s ({duration/60:.1f} min)")
                except:
                    pass
            
            if key_messages:
                print(f"      Key events:")
                for msg in key_messages[:5]:
                    print(msg)
    
    except Exception as exc:
        print(f"  ❌ Error processing logs: {exc}")
        import traceback
        traceback.print_exc()


def main():
    """Main monitoring function."""
    print("=" * 80)
    print("  Process Job Sharding Monitor")
    print("=" * 80)
    print(f"\n  Process Job ID: {PROCESS_JOB_ID}")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Region: {REGION}")
    
    # Step 1: Check Firestore job
    job_data = check_firestore_job()
    
    # Step 2: Check file pairing
    total_files, pairs = check_file_pairing(job_data)
    
    # Step 3: Check sharding logic
    expected_task_count = check_task_sharding(job_data, total_files)
    
    # Step 4: Check Firestore tasks
    task_list = check_firestore_tasks(job_data)
    
    # Step 5: Check Cloud Run execution
    execution_info = check_cloud_run_execution()
    
    # Step 6: Check task logs
    check_task_logs(execution_info)
    
    # Summary
    print_section("Summary")
    
    print("  Key Findings:")
    
    if job_data:
        firestore_total = job_data.get("total_files")
        if firestore_total:
            print(f"  ✅ total_files set: {firestore_total}")
        else:
            print(f"  ⚠️  total_files not set")
    
    if total_files:
        print(f"  ✅ File pairing: {total_files} pairs found")
    
    if expected_task_count:
        print(f"  ✅ Expected task_count: {expected_task_count}")
    
    if task_list:
        print(f"  ✅ Task documents: {len(task_list)} created")
        running_tasks = [t for t in task_list if t["status"] == "RUNNING"]
        completed_tasks = [t for t in task_list if t["status"] == "COMPLETED"]
        print(f"     - Running: {len(running_tasks)}")
        print(f"     - Completed: {len(completed_tasks)}")
    
    if execution_info:
        exec_task_count = execution_info.get("task_count", 0)
        exec_running = execution_info.get("running_count", 0)
        print(f"  ✅ Cloud Run execution: {exec_task_count} tasks")
        print(f"     - Currently running: {exec_running}")
        
        if exec_task_count > 1:
            print(f"  ✅ Sharding is active ({exec_task_count} tasks)")
        else:
            print(f"  ⚠️  Sharding may not be active (only {exec_task_count} task)")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

