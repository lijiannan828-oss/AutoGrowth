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
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

sys.path.append(str(backend_path))

from app.core.config import settings
from app.services.pipeline_status_service import PipelineStatusService
from app.services.google_oauth_service import retrieve_refresh_token, _token_collection
from app.core.firestore import get_firestore_client

# Target Token from user report
TARGET_TOKEN_ID = "token_c743d1e595ff460aa30c5643a71869c3"

def check_token_validity(token_ref, description):
    print(f"\nTesting Token: {token_ref} ({description})")
    try:
        # 1. Try to retrieve (decrypt)
        try:
            refresh_token = retrieve_refresh_token(token_ref)
            print(f"  ✅ Retrieval/Decryption SUCCESS.")
            print(f"     Ref Token Preview: {refresh_token[:5]}...{refresh_token[-5:]}")
        except Exception as e:
            print(f"  ❌ Retrieval/Decryption FAILED: {str(e)}")
            print(f"     Possible causes: Token ID doesn't exist, or OAUTH_TOKEN_ENCRYPTION_KEY mismatch.")
            return False

        # 2. Try to refresh (validate with Google)
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        
        try:
            print("  🔄 Attempting to refresh access token with Google...")
            creds.refresh(Request())
            if creds.valid:
                print("  ✅ Token Refresh SUCCESS! Access Token obtained.")
                return True
            else:
                print("  ❌ Token Refresh FAILED (creds.valid is False).")
                return False
        except Exception as e:
            print(f"  ❌ Token Refresh EXCEPTION: {str(e)}")
            if "invalid_grant" in str(e):
                 print("     -> CRITICAL: The refresh token has been revoked or expired.")
            return False
            
    except Exception as e:
        print(f"  ❌ Unexpected Error: {str(e)}")
        return False

def diagnose_drive_connection():
    print("=== Google Drive Connection Diagnostic (Deep Dive) ===")
    print(f"App Env: {settings.app_env}")
    print(f"Firestore Project: {settings.resolved_firestore_project}")
    
    # Check Key
    key = settings.oauth_token_encryption_key
    if key:
         print(f"Encryption Key Configured: Yes (Length: {len(key)})")
    else:
         print(f"Encryption Key Configured: ❌ NO")

    # 1. Check Configured Token in Settings
    configured_ref = settings.pipeline_default_token_ref
    print(f"\n[Env Var] PIPELINE_DEFAULT_TOKEN_REF: '{configured_ref}'")
    
    if configured_ref == TARGET_TOKEN_ID:
        print("  ✅ Matches the user-provided token ID.")
    else:
        print(f"  ⚠️  Does NOT match user-provided token ID: {TARGET_TOKEN_ID}")

    # 2. Test the Target Token specifically
    print(f"\n--- Testing Target Token: {TARGET_TOKEN_ID} ---")
    is_valid = check_token_validity(TARGET_TOKEN_ID, "User Specified Token")

    if is_valid:
        print("\n✅ The specific token is VALID and working.")
        print("If the frontend still fails, the issue might be:")
        print("1. The backend running process isn't seeing the same env vars as this script.")
        print("2. The folder ID being requested does not exist or is not accessible by this user.")
        
        # Test listing the root folder if token is valid
        try:
            print("\n--- Testing Drive API List (Root) ---")
            service = PipelineStatusService()
            # Force inject the valid token ref just in case logic picks another
            service._token_ref = TARGET_TOKEN_ID 
            drive = service._build_drive_service()
            if drive:
                print("  ✅ Drive Service built.")
                roots = settings.pipeline_gdrive_roots
                print(f"  Roots configured: {roots}")
                if roots:
                    lbl, fid = roots[0]
                    print(f"  Listing root '{lbl}' ({fid})...")
                    query = f"'{fid}' in parents and trashed=false"
                    items = list(service._drive_list(drive, query))
                    print(f"  ✅ Found {len(items)} items in root.")
                    if len(items) > 0:
                        print(f"     Sample: {items[0].get('name')}")
                else:
                    print("  ⚠️ No roots configured in PIPELINE_GDRIVE_ROOTS")
            else:
                print("  ❌ Failed to build Drive Service even with valid token check.")
        except Exception as e:
            print(f"  ❌ Drive API Error: {e}")

    else:
        print("\n❌ The specific token is INVALID or UNREACHABLE.")

if __name__ == "__main__":
    diagnose_drive_connection()
