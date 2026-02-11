# Google Drive Connection Diagnosis Report

## 1. Problem Analysis
The "Transfer Plan" tab fails to load Google Drive folders because the backend service cannot authenticate with the Google Drive API.

### Diagnosis Results
Running the diagnostic script `diagnose_drive_access.py` revealed:
1. **Missing Configuration**: `PIPELINE_DEFAULT_TOKEN_REF` environment variable is not set.
2. **No Valid Tokens**: Scanning Firestore showed no recent valid OAuth tokens in the `oauth_tokens` collection.

### Root Cause
The `PipelineStatusService` relies on a valid Refresh Token to access Google Drive. This token is obtained via the OAuth flow and stored in Firestore. The backend needs to know *which* token to use as the default system token, which is defined by `PIPELINE_DEFAULT_TOKEN_REF`.

Currently:
- No tokens exist (or are too old/revoked).
- The environment variable pointing to the default token is missing.

## 2. Solution Steps

To fix this in Production (and Development), you need to generate a new Token and configure the backend to use it.

### Step 1: Generate a New Refresh Token
You need to trigger the Google OAuth flow to authorize the application to access Google Drive.

**Option A: Via Frontend (If implemented)**
1. Log in to the AutoGrowth frontend.
2. Navigate to the "Settings" or "Profile" page (if available) where "Connect Google Drive" is located.
3. Click to connect/authorize.
4. This should call the `/oauth/exchange` API and store a new token in Firestore.

**Option B: Manual Token Generation (If no UI exists)**
You can use the provided `google-oauthlib-tool` or a temporary script, but the easiest way if the backend API is running is to call the `/oauth/exchange` endpoint manually with a code obtained from a browser.

### Step 2: Identify the Token ID
Once authorized, check the Firestore collection `[namespace]_oauth_tokens` (usually `default_oauth_tokens` or similar).
Find the most recent document. The Document ID (e.g., `token_abc123...`) is your **Token Ref**.

### Step 3: Update Configuration
Update the Cloud Run (Production) and local `.env` (Development) configuration:

**For Production (Cloud Run):**
```bash
gcloud run services update autogrowth-backend \
  --update-env-vars PIPELINE_DEFAULT_TOKEN_REF=your_new_token_ref \
  --region us-central1
```

**For Local Development:**
Add/Update this line in `backend/.env`:
```env
PIPELINE_DEFAULT_TOKEN_REF=your_new_token_ref
```

## 3. Verification
After updating the configuration:
1. Restart the backend service (if local).
2. Run `python scripts/diagnose_drive_access.py` again.
3. It should show `✅ Token retrieved successfully`.
4. Refresh the frontend "Transfer Plan" page, and the folders should load.

