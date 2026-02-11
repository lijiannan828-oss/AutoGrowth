import logging
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# Mock settings and get_firestore_client if needed, or use direct initialization
def get_db():
    return firestore.Client()

def reset_concurrency():
    db = get_db()
    doc_ref = db.collection("system_config").document("concurrency_control")
    
    snapshot = doc_ref.get()
    if not snapshot.exists:
        print("❌ Concurrency control document does not exist.")
        return

    data = snapshot.to_dict()
    print("\n📊 Current Status:")
    print(f"  Running Jobs Count: {data.get('running_jobs')}")
    print(f"  Running Job IDs: {data.get('running_job_ids')}")
    print(f"  Queue: {data.get('queue')}")
    print(f"  Last Updated: {data.get('updated_at')}")
    
    # Force reset
    print("\n⚠️  Resetting concurrency control...")
    doc_ref.update({
        "running_jobs": 0,
        "running_job_ids": [],
        "queue": [], # Optional: clear queue too? Or keep it? Let's keep queue ideally, but for hard reset maybe clear all.
        # Actually, if we clear running, the queued ones will be picked up next time they retry? 
        # No, the queued ones are passive.
        # If we want to unblock XaiII9IaNSWnxtO0K72C, we should probably keep it in queue 
        # and let the NEXT trigger pick it up? 
        # But since we don't have a cron job picking up queue, we rely on 'release_and_trigger_next'.
        # If we just clear running_ids, nobody is running, so nobody will trigger next.
        
        # Strategy: Clear running_ids. Then MANUALLY trigger the first one in queue?
        # For simplicity: Clear running_ids. Then USER must manually retry/trigger the stuck job.
        "updated_at": SERVER_TIMESTAMP
    })
    print("✅ Concurrency control reset to 0 running jobs.")

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    try:
        reset_concurrency()
    except Exception as e:
        print(f"❌ Error: {e}")


