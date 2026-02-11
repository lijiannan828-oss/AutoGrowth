"""Service responsible for enqueueing zip compression tasks."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import List

from google.cloud import run_v2
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.config import settings
from app.core.firestore import get_firestore_client
from app.schemas.auth import AuthenticatedUser


class PipelineZipService:
    """Handle Firestore zip task creation and Cloud Run triggering."""

    def __init__(self) -> None:
        self._firestore = get_firestore_client()
        self._jobs_client = run_v2.JobsClient()
        self._job_name = settings.zip_job_name.strip()
        self._collection_name = "zip_tasks"
        self._temp_bucket = (
            settings.pipeline_temp_download_bucket or "vigloo-temp-downloads"
        )
        self._processed_bucket = settings.pipeline_gcs_processed_bucket or "vigloo_processed"

    def enqueue_zip_task(
        self,
        paths: List[str],
        current_user: AuthenticatedUser,
    ) -> str:
        normalized_paths = []
        for path in paths:
            path = path.strip()
            if not path:
                continue
            if path.startswith("gs://"):
                normalized_paths.append(path)
            else:
                # Default to processed bucket if path is relative
                # Remove leading slash if present to avoid double slashes
                clean_path = path.lstrip("/")
                normalized_paths.append(f"gs://{self._processed_bucket}/{clean_path}")

        doc_ref = self._firestore.collection(self._collection_name).document()
        zip_object = f"zip/{doc_ref.id}.zip"
        doc_ref.set(
            {
                "paths": normalized_paths,
                "status": "QUEUED",
                "zip_bucket": self._temp_bucket,
                "zip_object": zip_object,
                "requested_by": current_user.email,
                "requested_by_name": current_user.name,
                "status_message": "等待打包任务开始",
                "created_at": SERVER_TIMESTAMP,
                "updated_at": SERVER_TIMESTAMP,
            }
        )

        self._trigger_zip_worker(doc_ref.id)
        return doc_ref.id

    # ------------------------------------------------------------------ internal
    def _trigger_zip_worker(self, task_id: str) -> None:
        if not task_id:
            raise ValueError("缺少 ZIP 任务 ID")

        if settings.app_env == "development":
            env = os.environ.copy()
            env["ZIP_TASK_ID"] = task_id
            # Calculate backend root (assuming this file is in app/services/)
            from pathlib import Path
            current_file = Path(__file__).resolve()
            # app/services/pipeline_zip_service.py -> app/services/ -> app/ -> backend/
            backend_root = current_file.parent.parent.parent
            
            env["PYTHONPATH"] = str(backend_root)
            
            try:
                process = subprocess.Popen(
                    [sys.executable, "-m", "app.workers.zip_compress.main"],
                    env=env,
                    cwd=str(backend_root),
                )
                print(
                    f"🚀 [DEV] 已在本地后台启动 Zip Worker (PID: {process.pid})，ZIP_TASK_ID={task_id}"
                )
            except Exception as exc:
                raise RuntimeError(f"本地 Zip Worker 启动失败：{exc}") from exc
            return

        if not self._job_name:
            raise RuntimeError("ZIP_JOB_NAME 未配置，无法触发 Cloud Run Job")

        env_vars = [
            run_v2.EnvVar(name="ZIP_TASK_ID", value=task_id),
        ]
        overrides = run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(env=env_vars),
            ]
        )
        request = run_v2.RunJobRequest(
            name=self._job_name,
            overrides=overrides,
        )

        try:
            operation = self._jobs_client.run_job(request=request)
            op_name = getattr(getattr(operation, "operation", None), "name", None)
            print(f"🚀 已触发 Zip Cloud Run Job: {self._job_name} (operation={op_name})")
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"触发 Zip Cloud Run Job 失败：{exc}") from exc


__all__ = ["PipelineZipService"]


