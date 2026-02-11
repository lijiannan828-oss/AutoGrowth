"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field(default="campaign-naming-backend")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    allowed_email_domains_raw: str = Field(
        default="example.com",
        validation_alias="ALLOWED_EMAIL_DOMAINS",
    )
    
    @property
    def allowed_email_domains(self) -> List[str]:
        """Parse comma-separated string into list of strings."""
        return [domain.strip() for domain in self.allowed_email_domains_raw.split(",") if domain.strip()]

    firebase_project_id: str = Field(default="", validation_alias="FIREBASE_PROJECT_ID")
    google_application_credentials: str = Field(
        default="", validation_alias="GOOGLE_APPLICATION_CREDENTIALS"
    )

    firestore_project_id: str = Field(
        default="", validation_alias="FIRESTORE_PROJECT_ID"
    )
    firestore_namespace: str = Field(
        default="", validation_alias="FIRESTORE_NAMESPACE"
    )
    firestore_emulator_host: str = Field(
        default="", validation_alias="FIRESTORE_EMULATOR_HOST"
    )

    # Fission (裂变) related settings
    gcp_project_id: str = Field(default="", validation_alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="us-central1", validation_alias="GCP_REGION")
    firestore_database: str = Field(default="(default)", validation_alias="FIRESTORE_DATABASE")
    fission_bucket: str = Field(default="", validation_alias="FISSION_BUCKET")
    fission_upload_bucket: str = Field(default="vigloo-fission-uploads", validation_alias="FISSION_UPLOAD_BUCKET")

    # Subtitle (字幕) related settings — 使用 vigloo-fission-uploads 桶内 vigloo-subtitle-uploads/ 前缀
    subtitle_bucket: str = Field(default="vigloo-fission-uploads", validation_alias="SUBTITLE_BUCKET")

    # TTS (文字转语音) related settings — 使用 vigloo-fission-uploads 桶内 vigloo-tts-uploads/ 前缀
    tts_bucket: str = Field(default="vigloo-fission-uploads", validation_alias="TTS_BUCKET")

    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    cloud_sql_connection_name: str = Field(
        default="", validation_alias="CLOUD_SQL_CONNECTION_NAME"
    )
    database_name: str = Field(default="auto_growth", validation_alias="DATABASE_NAME")
    database_user: str = Field(default="appdev", validation_alias="DATABASE_USER")
    database_password: str = Field(default="", validation_alias="DATABASE_PASSWORD")
    # For IAM authentication, use IAM database user (service account email or custom IAM user)
    use_iam_auth: bool = Field(default=False, validation_alias="USE_IAM_AUTH")
    google_sheets_id: str = Field(default="", validation_alias="GOOGLE_SHEETS_ID")

    google_oauth_client_id: str = Field(
        default="", validation_alias="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_oauth_client_secret: str = Field(
        default="", validation_alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    google_oauth_redirect_uri: str = Field(
        default="", validation_alias="GOOGLE_OAUTH_REDIRECT_URI"
    )
    oauth_token_encryption_key: str = Field(
        default="", validation_alias="OAUTH_TOKEN_ENCRYPTION_KEY"
    )
    pipeline_status_mock_file: str = Field(
        default="", validation_alias="PIPELINE_STATUS_MOCK_FILE"
    )
    pipeline_gcs_source_bucket: str = Field(
        default="vigloo_source", validation_alias="PIPELINE_GCS_SOURCE_BUCKET"
    )
    pipeline_gcs_processed_bucket: str = Field(
        default="vigloo_processed", validation_alias="PIPELINE_GCS_PROCESSED_BUCKET"
    )
    pipeline_gdrive_roots_raw: str = Field(
        default="", validation_alias="PIPELINE_GDRIVE_ROOTS"
    )
    pipeline_default_token_ref: str = Field(
        default="", validation_alias="PIPELINE_DEFAULT_TOKEN_REF"
    )
    transfer_job_name: str = Field(
        default="", validation_alias="TRANSFER_JOB_NAME"
    )
    process_job_name: str = Field(
        default="", validation_alias="PROCESSOR_JOB_NAME"
    )
    zip_job_name: str = Field(
        default="", validation_alias="ZIP_JOB_NAME"
    )
    pipeline_temp_download_bucket: str = Field(
        default="vigloo-temp-downloads", validation_alias="PIPELINE_TEMP_DOWNLOAD_BUCKET"
    )
    download_signed_url_ttl_seconds: int = Field(
        default=3600, validation_alias="DOWNLOAD_SIGNED_URL_TTL"
    )
    max_concurrent_jobs: int = Field(
        default=8, validation_alias="MAX_CONCURRENT_JOBS"
    )

    # CORS: comma-separated list of allowed origins for frontend (e.g., Firebase Hosting domains)
    frontend_origins_raw: str = Field(default="", validation_alias="FRONTEND_ORIGINS")
    @property
    def frontend_origins(self) -> List[str]:
        return [o.strip() for o in self.frontend_origins_raw.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def resolved_firestore_project(self) -> str:
        """Prefer explicit Firestore project, fallback to Firebase project."""
        return self.firestore_project_id or self.firebase_project_id

    @property
    def pipeline_gdrive_roots(self) -> List[tuple[str, str]]:
        roots: List[tuple[str, str]] = []
        if not self.pipeline_gdrive_roots_raw:
            return roots
        for item in self.pipeline_gdrive_roots_raw.split(","):
            if not item.strip() or ":" not in item:
                continue
            label, folder_id = item.split(":", 1)
            label = label.strip()
            folder_id = folder_id.strip()
            if label and folder_id:
                roots.append((label, folder_id))
        return roots


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
