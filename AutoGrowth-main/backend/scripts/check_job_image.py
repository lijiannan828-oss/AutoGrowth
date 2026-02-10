import os
import sys
from pathlib import Path
from google.cloud import run_v2
from datetime import datetime, timezone

# Setup path & credentials
backend_path = Path(__file__).parent.parent
sys.path.append(str(backend_path))
service_account_path = backend_path / "service-account.json"
if service_account_path.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(service_account_path)

def check_job_image():
    print("=== Checking Cloud Run Job Image Status ===")
    project_id = "fleet-blend-469520-n7"
    location = "us-central1"
    job_name = "drama-processor-job"
    
    client = run_v2.JobsClient()
    full_name = f"projects/{project_id}/locations/{location}/jobs/{job_name}"
    
    try:
        job = client.get_job(name=full_name)
        image = job.template.template.containers[0].image
        update_time = job.update_time
        
        print(f"✅ Job Found: {job_name}")
        print(f"🖼️ Current Image: {image}")
        
        # Handle timestamp
        updated_at = update_time
        if updated_at:
            # Convert to readable string
            # Note: protobuf timestamp might need conversion
            now = datetime.now(timezone.utc)
            # Assuming job.update_time is a standard datetime object after client parsing
            # If not, we might need to access seconds/nanos directly
            
            print(f"🕒 Last Updated: {updated_at}")
            
            # Simple diff check
            try:
                diff = now - updated_at
                print(f"⏱️ Time since update: {diff}")
                
                if diff.total_seconds() < 300:  # 5 minutes
                    print("🔥 FRESH DEPLOY DETECTED (Updated < 5 mins ago)")
                elif diff.total_seconds() < 3600:
                    print("✅ RECENTLY UPDATED (Updated < 1 hour ago)")
                else:
                    print("⚠️ OLD DEPLOY (Updated > 1 hour ago)")
            except Exception as e:
                print(f"⚠️ Time calc error: {e}")
        
    except Exception as e:
        print(f"❌ Failed to get job details: {e}")

if __name__ == "__main__":
    check_job_image()

