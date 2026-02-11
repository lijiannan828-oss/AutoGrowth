"""Service responsible for enqueuing pipeline transfer jobs."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Dict

from google.cloud import run_v2
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.config import settings
from app.core.firestore import get_firestore_client
from app.schemas.auth import AuthenticatedUser
from app.schemas.pipeline import TransferJobRequest, TransferJobResponse


class PipelineTransferService:
    """Handle Firestore job creation and Cloud Run job triggering."""

    def __init__(self) -> None:
        self._firestore = get_firestore_client()
        self._jobs_client = run_v2.JobsClient()
        self._job_name = settings.transfer_job_name.strip()
        # NOTE: 前端当前订阅 `pipeline_jobs` 集合，因此暂不引入 namespace 前缀，避免读取不到数据
        self._collection_name = "pipeline_jobs"

    def enqueue_transfer_job(
        self,
        payload: TransferJobRequest,
        current_user: AuthenticatedUser,
    ) -> TransferJobResponse:
        if not payload.include_folders:
            raise ValueError("至少需要选择一个目录进行传输")

        if not settings.pipeline_default_token_ref:
            raise RuntimeError("PIPELINE_DEFAULT_TOKEN_REF 未配置，无法触发传输 Job")

        doc_ref = self._firestore.collection(self._collection_name).document()
        doc_body = self._build_job_document(payload, current_user)
        doc_ref.set(doc_body)
        print(f"📝 Firestore pipeline job created: {doc_ref.id}")

        self._trigger_cloud_run_job(doc_ref.id, settings.pipeline_default_token_ref)

        return TransferJobResponse(job_id=doc_ref.id, status="QUEUED")

    # ------------------------------------------------------------------ Internal helpers
    def _build_job_document(
        self,
        payload: TransferJobRequest,
        current_user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        created_by = current_user.email
        # 只去掉路径两端的斜杠，保留其他字符（包括末尾空格）
        # 因为文件夹名可能包含末尾空格，strip() 会错误地去掉这些空格
        include_folders = [
            folder.strip("/") for folder in payload.include_folders if folder.strip("/")
        ]

        return {
            "drama_name": payload.drama_name,
            "gdrive_path": payload.gdrive_path,
            "include_folders": include_folders,
            "status": "QUEUED",
            "stage": 1,
            "progress": "等待传输",
            "created_by": created_by,
            "created_by_name": current_user.name,
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
            "oauth_refresh_token_ref": settings.pipeline_default_token_ref,
            "gcs_source_bucket": settings.pipeline_gcs_source_bucket,
            "auth_mode": "dev_default" if current_user.is_dev_user else "user",
            "last_event": {
                "type": "REQUEST_SUBMITTED",
                "user": created_by,
            },
        }

    def _trigger_cloud_run_job(self, job_document_id: str, token_ref: str) -> None:
        if settings.app_env == "development":
            env = os.environ.copy()
            env["JOB_ID"] = job_document_id
            env["REFRESH_TOKEN_REF"] = token_ref
            env.setdefault("PYTHONPATH", os.getcwd())
            try:
                process = subprocess.Popen(
                    [sys.executable, "-m", "app.workers.transfer.main"],
                    env=env,
                    cwd=os.getcwd(),
                )
                print(
                    f"🚀 [DEV] 已在本地后台启动 Transfer Worker (PID: {process.pid})，JOB_ID={job_document_id}"
                )
            except Exception as exc:
                raise RuntimeError(f"本地启动 Worker 失败：{exc}") from exc
            return

        if not self._job_name:
            raise RuntimeError("TRANSFER_JOB_NAME 未配置，无法触发 Cloud Run Job")

        env_vars = [
            run_v2.EnvVar(name="JOB_ID", value=job_document_id),
            run_v2.EnvVar(name="REFRESH_TOKEN_REF", value=token_ref),
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
            print(f"🚀 已触发 Cloud Run Job: {self._job_name} (operation={op_name})")
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"触发 Cloud Run Job 失败：{exc}") from exc

