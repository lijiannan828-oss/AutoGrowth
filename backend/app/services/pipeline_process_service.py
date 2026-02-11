"""Service responsible for process worker retry jobs."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import List, Tuple

from google.cloud import run_v2
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.config import settings
from app.core.firestore import get_firestore_client
from app.schemas.auth import AuthenticatedUser
from app.services.pipeline_discovery_service import discover_file_pairs, detect_language
from app.services.concurrency_service import ConcurrencyService


def _parse_gs_uri(path: str) -> Tuple[str, str]:
    if not path or not path.startswith("gs://"):
        raise ValueError(f"无效的 GCS 路径：{path}")
    remainder = path[5:]
    if "/" not in remainder:
        raise ValueError(f"缺少对象路径：{path}")
    bucket, blob_path = remainder.split("/", 1)
    if not bucket or not blob_path:
        raise ValueError(f"缺少 bucket 或对象：{path}")
    return bucket, blob_path


class PipelineProcessService:
    """Encapsulate Firestore + Cloud Run orchestration for process worker."""

    def __init__(self) -> None:
        self._firestore = get_firestore_client()
        self._jobs_client = run_v2.JobsClient()
        self._process_job_name = settings.process_job_name.strip()
        self._jobs_collection = "pipeline_jobs"
        self._failures_collection = "processing_failures"

    def enqueue_retry_job(self, failure_id: str, current_user: AuthenticatedUser) -> str:
        failure_ref = self._firestore.collection(self._failures_collection).document(failure_id)
        failure_snapshot = failure_ref.get()
        if not failure_snapshot.exists:
            raise ValueError("未找到指定的失败记录")
        failure_data = failure_snapshot.to_dict() or {}

        status = (failure_data.get("status") or "").upper()
        if status == "RESOLVED":
            raise ValueError("该失败记录已被标记为 RESOLVED，无需重试")

        video_path = failure_data.get("video_gcs_path")
        subtitle_path = failure_data.get("subtitle_gcs_path")
        drama_name = failure_data.get("drama_name")
        language = failure_data.get("language")
        episode = failure_data.get("episode")

        if not video_path or not subtitle_path or not drama_name:
            raise RuntimeError("失败记录缺少必要字段，无法创建重试任务")

        video_bucket, _ = _parse_gs_uri(video_path)

        job_ref = self._firestore.collection(self._jobs_collection).document()
        doc_body = {
            "drama_name": drama_name,
            "status": "QUEUED",
            "stage": 2,
            "type": "retry",
            "progress": "等待重试任务开始",
            "target_video_path": video_path,
            "target_subtitle_path": subtitle_path,
            "related_failure_id": failure_id,
            "process_languages": [language] if language else [],
            "retry_episode": episode,
            "gcs_source_bucket": video_bucket,
            "gcs_processed_bucket": settings.pipeline_gcs_processed_bucket,
            "total_files": 1,  # Retry job processes exactly 1 file
            "processed_files": 0,  # Initial count: 0 successful
            "failed_files": 0,  # Initial count: 0 failed
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
            "created_by": current_user.email,
            "created_by_name": current_user.name,
            "auth_mode": "dev_default" if current_user.is_dev_user else "user",
            "last_event": {
                "type": "RETRY_REQUESTED",
                "user": current_user.email,
                "timestamp": SERVER_TIMESTAMP,
            },
        }
        job_ref.set(doc_body)

        failure_ref.update(
            {
                "status": "RETRYING",
                "retry_job_id": job_ref.id,
                "updated_at": SERVER_TIMESTAMP,
            }
        )

        # Retry job processes exactly 1 file, so task_count = 1
        self._trigger_process_worker(job_ref.id, total_files=1)
        return job_ref.id

    def trigger_manual_process_job(
        self,
        drama_name: str,
        file_paths: List[str],
        current_user: AuthenticatedUser | None = None,
    ) -> str:
        cleaned_paths = [path.strip().lstrip("/") for path in file_paths if path and path.strip()]
        if not drama_name.strip():
            raise ValueError("drama_name 不能为空")
        if not cleaned_paths:
            raise ValueError("需至少指定一个 file_paths 项")

        # Extract language codes from file paths
        # This allows filtering by selected languages when user selects specific language folders
        detected_languages = set()
        for path in cleaned_paths:
            lang = detect_language(path)
            if lang and lang != "unknown":
                # Normalize language key (e.g., "th_translated" -> "th")
                normalized_lang = lang.split("_")[0].split("-")[0].lower()
                detected_languages.add(normalized_lang)
        
        process_languages = sorted(detected_languages) if detected_languages else []
        if process_languages:
            print(f"📋 Extracted languages from file_paths: {process_languages}")

        # Discover file pairs using shared utility (same logic as worker)
        # This ensures consistent sorting and filtering
        # Pass process_languages to filter by selected languages
        # Pass cleaned_paths as allowed_paths to filter by selected files
        print(f"📁 [SERVICE] 开始发现文件配对:")
        print(f"   drama_name: {drama_name}")
        print(f"   cleaned_paths: {cleaned_paths}")
        print(f"   detected_languages: {detected_languages}")
        print(f"   allowed_paths: {set(cleaned_paths) if cleaned_paths else None}")
        
        try:
            pairs = discover_file_pairs(
                drama_name=drama_name.strip(),
                source_bucket=settings.pipeline_gcs_source_bucket,
                allowed_languages=detected_languages if detected_languages else None,
                allowed_paths=set(cleaned_paths) if cleaned_paths else None,
            )
            total_files = len(pairs)
            print(f"📊 [SERVICE] Discovered {total_files} file pairs for drama={drama_name}")
            print(f"   languages: {process_languages or 'all'}")
            print(f"   selected files: {len(cleaned_paths) if cleaned_paths else 'all'}")
            print(f"   allowed_paths 生效: {'是' if cleaned_paths else '否'}")
            
            # Log first few pairs for debugging
            if pairs:
                print(f"   前3个配对示例:")
                for i, pair in enumerate(pairs[:3]):
                    print(f"     {i+1}. ep{pair.episode} ({pair.language}): {pair.video_path.split('/')[-1]}")
        except TypeError as e:
            # If discovery fails due to API mismatch, log detailed error
            print(f"❌ [SERVICE] discover_file_pairs TypeError: {e}")
            print(f"   这可能是因为代码版本不匹配")
            print(f"   请检查 pipeline_discovery_service.py 是否支持 allowed_paths 参数")
            raise
        except Exception as exc:
            # If discovery fails, set total_files to None and let worker set it
            print(f"⚠️ [SERVICE] Failed to discover file pairs: {exc}, worker will set total_files")
            import traceback
            traceback.print_exc()
            total_files = None

        job_ref = self._firestore.collection(self._jobs_collection).document()
        doc_body = {
            "drama_name": drama_name.strip(),
            "status": "QUEUED",
            "stage": 1,
            "type": "manual",
            "progress": "等待压制任务开始",
            "transfer_completed": True,
            "manual_file_paths": cleaned_paths,
            "process_languages": process_languages,  # Set extracted languages for worker filtering
            "gcs_source_bucket": settings.pipeline_gcs_source_bucket,
            "gcs_processed_bucket": settings.pipeline_gcs_processed_bucket,
            "total_files": total_files,  # Set from discovery, or None if discovery failed
            "processed_files": 0,  # Initial count: 0 successful
            "failed_files": 0,  # Initial count: 0 failed
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
            "created_by": current_user.email if current_user else "system",
            "created_by_name": current_user.name if current_user else "system",
            "auth_mode": "dev_default" if (current_user and current_user.is_dev_user) else "user",
            "last_event": {
                "type": "MANUAL_PROCESS_REQUESTED",
                "user": current_user.email if current_user else "system",
                "timestamp": SERVER_TIMESTAMP,
            },
        }
        job_ref.set(doc_body)
        self._trigger_process_worker(job_ref.id, total_files=total_files)
        return job_ref.id

    # --------------------------------------------------------------------- internal
    def _trigger_process_worker(self, job_document_id: str, total_files: int | None = None) -> None:
        """Trigger process worker with optional task_count based on total_files.
        
        Args:
            job_document_id: Firestore job document ID
            total_files: Total number of files to process (used to calculate task_count)
        """
        # Step 0: Acquire job slot (Global Concurrency Control)
        print(f"🔐 [TRIGGER] 开始获取 job slot: {job_document_id}")
        concurrency_service = ConcurrencyService()
        can_start, slot_message = concurrency_service.acquire_job_slot(job_document_id)
        
        print(f"🔐 [TRIGGER] acquire_job_slot 返回: can_start={can_start}, message={slot_message}")
        
        job_ref = self._firestore.collection(self._jobs_collection).document(job_document_id)
        
        if not can_start:
            # Job is queued
            print(f"⏳ [TRIGGER] Job {job_document_id} is queued: {slot_message}")
            print(f"⏳ [TRIGGER] 当前并发控制状态: {slot_message}")
            job_ref.update({
                "status": "QUEUED",
                "progress": f"等待执行 ({slot_message})",
                "updated_at": SERVER_TIMESTAMP,
            })
            return

        # Job acquired slot, proceed to trigger
        print(f"✅ Job {job_document_id} acquired slot: {slot_message}")
        
        if settings.app_env == "development":
            env = os.environ.copy()
            env["JOB_ID"] = job_document_id
            env.setdefault("PYTHONPATH", os.getcwd())
            try:
                process = subprocess.Popen(
                    [sys.executable, "-m", "app.workers.process.main"],
                    env=env,
                    cwd=os.getcwd(),
                )
                print(
                    f"🚀 [DEV] 已在本地后台启动 Process Worker (PID: {process.pid})，JOB_ID={job_document_id}"
                )
            except Exception as exc:
                raise RuntimeError(f"本地启动 Process Worker 失败：{exc}") from exc
            return

        if not self._process_job_name:
            raise RuntimeError("PROCESSOR_JOB_NAME 未配置，无法触发 Cloud Run Job")

        env_vars = [run_v2.EnvVar(name="JOB_ID", value=job_document_id)]
        
        # Calculate task_count based on total_files
        # Strategy: Limit each Task to max 3 files to prevent timeout
        # For >100 files: task_count = ceil(total / 3), capped at 100
        # For <=100 files: task_count = total_files (1:1 mapping)
        task_count = None
        if total_files is not None and total_files > 0:
            if total_files <= 100:
                # Small batch: 1:1 mapping
                task_count = total_files
            else:
                # Large batch: limit each Task to max 3 files
                # task_count = ceil(total / 3), but cap at 100 to prevent DB pressure
                import math
                task_count = min(math.ceil(total_files / 3), 100)
            print(f"📊 Calculated task_count={task_count} for total_files={total_files} (max 3 files per task)")
        
        overrides_kwargs = {
            "container_overrides": [
                run_v2.RunJobRequest.Overrides.ContainerOverride(env=env_vars),
            ]
        }
        
        # Only set task_count if we have a valid value
        if task_count is not None:
            overrides_kwargs["task_count"] = task_count
        
        overrides = run_v2.RunJobRequest.Overrides(**overrides_kwargs)

        request = run_v2.RunJobRequest(
            name=self._process_job_name,
            overrides=overrides,
        )

        try:
            operation = self._jobs_client.run_job(request=request)
            op_name = getattr(getattr(operation, "operation", None), "name", None)
            print(
                f"🚀 已触发 Process Cloud Run Job: {self._process_job_name} "
                f"(operation={op_name}, task_count={task_count})"
            )
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"触发 Process Cloud Run Job 失败：{exc}") from exc

