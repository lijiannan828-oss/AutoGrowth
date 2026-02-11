import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime

# Initialize Firestore
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'projectId': 'fleet-blend-469520-n7',
    })

db = firestore.client()

def inspect_job(job_id):
    print(f"🔍 Inspecting Job: {job_id}")
    
    # 1. Get Job Document
    job_ref = db.collection('pipeline_jobs').document(job_id)
    job_doc = job_ref.get()
    
    if not job_doc.exists:
        print(f"❌ Job {job_id} not found!")
        return

    data = job_doc.to_dict()
    print(f"\n📊 [Job Summary]")
    print(f"  Drama Name: {data.get('drama_name')}")
    print(f"  Status: {data.get('status')}")
    print(f"  Total Files: {data.get('total_files', 'N/A')}")
    print(f"  Processed Files: {data.get('processed_files', 0)}")
    print(f"  Failed Files: {data.get('failed_files', 0)}")
    print(f"  Created At: {data.get('created_at')}")
    print(f"  Updated At: {data.get('updated_at')}")

    # 2. Get Tasks Subcollection
    tasks_ref = job_ref.collection('tasks')
    tasks = list(tasks_ref.stream())
    
    print(f"\n🧩 [Sharding / Tasks Analysis]")
    print(f"  Total Task Documents (Shards): {len(tasks)}")
    
    if not tasks:
        print("  ⚠️ No tasks found. Worker might not have started or initialized tasks yet.")
        return

    completed = 0
    running = 0
    failed = 0
    pending = 0
    
    task_details = []

    for task in tasks:
        t_data = task.to_dict()
        status = t_data.get('status', 'UNKNOWN')
        task_index = t_data.get('task_index')
        
        if status == 'COMPLETED': completed += 1
        elif status == 'RUNNING': running += 1
        elif status == 'FAILED': failed += 1
        else: pending += 1
        
        # Calculate processing time per task
        start = t_data.get('start_time')
        end = t_data.get('end_time')
        duration = "N/A"
        if start and end:
            try:
                # Handle Firestore Timestamp objects
                if hasattr(start, 'timestamp') and hasattr(end, 'timestamp'):
                    diff = end.timestamp() - start.timestamp()
                    duration = f"{diff:.1f}s"
            except:
                pass

        processed_count = len(t_data.get('success_files', []))
        
        task_details.append({
            'index': task_index,
            'status': status,
            'processed': processed_count,
            'duration': duration,
            'updated': t_data.get('updated_at')
        })

    print(f"  Active Shards (Tasks): {len(tasks)}")
    print(f"  Status Distribution: ✅ {completed} | 🏃 {running} | ❌ {failed} | ⏳ {pending}")

    print(f"\n📋 [Detailed Task Logs (Top 20)]")
    # Sort by index
    task_details.sort(key=lambda x: int(x['index']) if x['index'] is not None else -1)
    
    print(f"  {'Index':<6} | {'Status':<10} | {'Files':<6} | {'Duration':<10} | {'Last Update'}")
    print("-" * 60)
    for t in task_details[:20]:
        print(f"  {str(t['index']):<6} | {t['status']:<10} | {str(t['processed']):<6} | {t['duration']:<10} | {t['updated']}")
    
    if len(task_details) > 20:
        print(f"  ... and {len(task_details) - 20} more tasks.")

if __name__ == "__main__":
    inspect_job("akln3K9gWpb6dJdJuWbE")


