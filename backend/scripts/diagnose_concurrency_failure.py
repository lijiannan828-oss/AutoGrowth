import os
import sys
import datetime
from pathlib import Path
from google.cloud import firestore

# Setup path
backend_path = Path(__file__).parent.parent
sys.path.append(str(backend_path))

# Load env if needed
from dotenv import load_dotenv
env_path = backend_path / ".env"
load_dotenv(env_path)

# Initialize Firestore
# Force unset emulator host to ensure we hit production
if "FIRESTORE_EMULATOR_HOST" in os.environ:
    del os.environ["FIRESTORE_EMULATOR_HOST"]

# Set credentials path explicitly
service_account_path = backend_path / "service-account.json"
if service_account_path.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(service_account_path)

try:
    db = firestore.Client(project="fleet-blend-469520-n7")
    print(f"✅ Connected to Firestore (Project: fleet-blend-469520-n7)")
except Exception as e:
    print(f"❌ Failed to connect to Firestore: {e}")
    sys.exit(1)

def diagnose():
    print("\n=== 1. Inspecting Global Lock (system_config/concurrency_control) ===")
    doc_ref = db.collection("system_config").document("concurrency_control")
    doc = doc_ref.get()
    
    max_concurrent_jobs = 8  # Default fallback for diagnostic script display
    
    if doc.exists:
        data = doc.to_dict()
        max_concurrent_jobs = data.get('max_concurrent_jobs', 8)
        print(f"📄 Document exists.")
        print(f"   - max_concurrent_jobs: {max_concurrent_jobs}")
        print(f"   - running_jobs (count): {data.get('running_jobs')}")
        print(f"   - running_job_ids: {data.get('running_job_ids')}")
        print(f"   - queue: {data.get('queue')}")
        print(f"   - updated_at: {data.get('updated_at')}")
    else:
        print("❌ Document 'system_config/concurrency_control' DOES NOT EXIST!")

    print("\n=== 2. Inspecting Recent Jobs (pipeline_jobs) ===")
    # Get last 5 jobs
    jobs = db.collection("pipeline_jobs")\
             .order_by("created_at", direction=firestore.Query.DESCENDING)\
             .limit(10)\
             .stream()
    
    found_running = []
    for job in jobs:
        d = job.to_dict()
        jid = job.id
        status = d.get("status")
        drama = d.get("drama_name")
        created = d.get("created_at")
        updated = d.get("updated_at")
        
        # Convert timestamps to readable string
        c_str = created.strftime("%H:%M:%S") if created else "N/A"
        u_str = updated.strftime("%H:%M:%S") if updated else "N/A"
        
        print(f"🎬 Job ID: {jid} | Status: {status}")
        print(f"   - Drama: {drama}")
        print(f"   - Created: {c_str} | Updated: {u_str}")
        
        if status in ["PROCESSING", "QUEUED", "RUNNING"]:
            found_running.append(jid)

    print("\n=== 3. Analysis ===")
    if doc.exists:
        locked_ids = set(data.get('running_job_ids', []))
        running_ids = set(found_running)
        
        print(f"Jobs currently in PROCESSING/QUEUED state: {len(running_ids)}")
        print(f"Jobs locked in Concurrency Control: {len(locked_ids)}")
        
        # Logic check: running jobs should be tracked
        # Note: QUEUED jobs that are IN THE QUEUE are NOT in running_job_ids, so this check is tricky.
        # We only care if a job is running but NOT in lock AND NOT in queue.
        queue = set(data.get('queue', []))
        
        untracked_running = []
        for rid in running_ids:
            if rid not in locked_ids and rid not in queue:
                untracked_running.append(rid)
        
        if untracked_running:
            # Check if these are stale/zombie jobs?
            print(f"❌ POTENTIAL LEAK: These jobs are status=PROCESSING/QUEUED but NOT in running_job_ids AND NOT in queue: {untracked_running}")
        else:
            print("✅ All active jobs are properly tracked (either Running or Queued).")
            
        if len(locked_ids) > max_concurrent_jobs:
             print(f"❌ LOCK VIOLATION: concurrency_control has {len(locked_ids)} jobs (>{max_concurrent_jobs}) marked as running!")
        else:
             print(f"✅ Lock count ({len(locked_ids)}) is within limit ({max_concurrent_jobs}).")

if __name__ == "__main__":
    diagnose()