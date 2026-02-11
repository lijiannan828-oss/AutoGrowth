"""Google Sheets API client initialization."""

import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from app.core.config import settings


def get_gspread_client() -> gspread.Client:
    """Initialize and return a gspread client using service account credentials."""
    creds_path = settings.google_application_credentials
    # Resolve relative or fallback to local service account for dev
    if creds_path and not os.path.isabs(creds_path):
        creds_path = str(Path(__file__).parent.parent.parent / creds_path)
    default_local_creds = Path(__file__).parent.parent.parent / "service-account.json"
    if not creds_path or not os.path.exists(creds_path):
        if default_local_creds.exists():
            creds_path = str(default_local_creds)
        else:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set or file missing")
    
    credentials = Credentials.from_service_account_file(
        creds_path,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ],
    )
    return gspread.authorize(credentials)
