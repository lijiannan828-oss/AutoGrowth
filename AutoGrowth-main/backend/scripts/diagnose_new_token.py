import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import firestore

# Explicitly load .env from backend directory
backend_path = Path(__file__).parent.parent
env_path = backend_path / ".env"
load_dotenv(env_path)
sys.path.append(str(backend_path))

from app.core.config import settings
from app.services.pipeline_status_service import PipelineStatusService
from app.services.google_oauth_service import retrieve_refresh_token

# User provided Token ID
TARGET_TOKEN_ID = "token_0dfe8b9823e9465995646eee04f872f6"

def diagnose_new_token():
    print(f"=== Diagnosing New Token: {TARGET_TOKEN_ID} ===")
    print(f"Firestore Namespace: {settings.firestore_namespace}")
    
    # 1. Verify Token Retrieval & Refresh
    try:
        refresh_token = retrieve_refresh_token(TARGET_TOKEN_ID)
        print(f"✅ Token retrieval SUCCESS (Decrypted).")
        
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        
        print("🔄 Refreshing access token...")
        creds.refresh(Request())
        if creds.valid:
            print("✅ Token refresh SUCCESS. Access Token is valid.")
        else:
            print("❌ Token refresh FAILED. Creds invalid.")
            return
            
    except Exception as e:
        print(f"❌ Token Check Failed: {e}")
        return

    # 2. Verify Drive API Access with this Token
    print("\n=== Testing Drive API with New Token ===")
    try:
        service = PipelineStatusService()
        # Force inject the new token ref to bypass current env var
        service._token_ref = TARGET_TOKEN_ID
        
        drive = service._build_drive_service()
        if not drive:
            print("❌ Failed to build Drive Service.")
            return
            
        print("✅ Drive Service built.")
        
        roots = settings.pipeline_gdrive_roots
        print(f"Configured Roots: {roots}")
        
        if not roots:
            print("⚠️ No roots configured to test.")
            return
            
        for label, folder_id in roots:
            print(f"\nTesting Root: {label} ({folder_id})")
            try:
                # Try to list children of this root
                query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                items = list(service._drive_list(drive, query))
                print(f"  ✅ Found {len(items)} sub-folders.")
                if len(items) > 0:
                    print(f"     Sample: {items[0].get('name')} ({items[0].get('id')})")
                else:
                    print("     (Folder is empty or not accessible)")
            except Exception as e:
                print(f"  ❌ Failed to list root: {e}")
                if "File not found" in str(e):
                    print("     -> The Root Folder ID might be incorrect or shared permission missing.")

    except Exception as e:
        print(f"❌ Drive API Test Failed: {e}")

if __name__ == "__main__":
    diagnose_new_token()

