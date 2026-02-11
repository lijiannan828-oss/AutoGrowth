"""Eventarc relay endpoint for triggering processor jobs."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Request
from google.cloud import firestore
from google.cloud import run_v2

from app.core.config import settings
from app.core.firestore import get_firestore_client
from app.services.pipeline_discovery_service import discover_file_pairs
from app.services.concurrency_service import ConcurrencyService
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from google.cloud.firestore_v1.transforms import Increment

router = APIRouter(prefix="/relay", tags=["relay"])
logger = logging.getLogger(__name__)

FIRESTORE_COLLECTION = "pipeline_jobs"
PROCESS_SIGNAL_SUFFIX = "_PROCESS_NOW.txt"

_jobs_client: run_v2.JobsClient | None = None


def _get_firestore_client() -> firestore.Client:
    """Get Firestore client (lazy initialization)."""
    return get_firestore_client()


def _get_jobs_client() -> run_v2.JobsClient:
    """Get Cloud Run Jobs client (lazy initialization)."""
    global _jobs_client
    if _jobs_client is None:
        _jobs_client = run_v2.JobsClient()
    return _jobs_client


def _extract_drama_name(object_name: str | None) -> str | None:
    if not object_name:
        return None
    segments = [part for part in object_name.split("/") if part]
    if not segments:
        return None
    return segments[0]


def _find_latest_ready_job(drama_name: str, request_id: str | None = None) -> Tuple[str, Dict[str, Any]] | Tuple[None, None]:
    """Find the latest ready job for a given drama_name.
    
    A job is considered "ready" if:
    - transfer_completed == True
    - stage == 1 or stage is None
    
    Returns the most recent job (by updated_at) that matches these conditions.
    
    Uses database-level sorting (order_by) for better performance.
    Falls back to memory sorting if index is not ready yet.
    
    Requires Firestore composite index:
    - Collection: pipeline_jobs
    - Fields: drama_name (Ascending), updated_at (Descending)
    """
    firestore_client = _get_firestore_client()
    
    # Try database-level sorting first (requires composite index)
    query_with_order = (
        firestore_client.collection(FIRESTORE_COLLECTION)
        .where("drama_name", "==", drama_name)
        .order_by("updated_at", direction=firestore.Query.DESCENDING)
        .limit(20)
    )
    
    try:
        # Try database-level sorting
        for snapshot in query_with_order.stream():
            data = snapshot.to_dict() or {}
            if not data:
                continue
            transfer_completed = bool(data.get("transfer_completed"))
            stage = data.get("stage")
            if transfer_completed and (stage == 1 or stage is None):
                logger.info(
                    "[RELAY] Ready job found (database sort)",
                    extra={
                        "request_id": request_id,
                        "job_id": snapshot.id,
                        "drama_name": drama_name,
                        "updated_at": str(data.get("updated_at")),
                    }
                )
                print(f"[RELAY-{request_id or 'N/A'}] ✅ Found ready job (database sort): job_id={snapshot.id}, drama={drama_name}", flush=True)
                return snapshot.id, data
        
        logger.warning(
            "[RELAY] No ready job found",
            extra={
                "request_id": request_id,
                "drama_name": drama_name,
            }
        )
        print(f"[RELAY-{request_id or 'N/A'}] ⚠️  No ready job found: drama={drama_name}", flush=True)
        return None, None
    
    except Exception as exc:
        error_msg = str(exc)
        # Check if index is building
        if "index is currently building" in error_msg.lower() or "requires an index" in error_msg.lower():
            logger.warning(
                "[RELAY] Index building, using memory sort fallback",
                extra={
                    "request_id": request_id,
                    "drama_name": drama_name,
                    "error": error_msg,
                }
            )
            print(f"[RELAY-{request_id or 'N/A'}] ⚠️  Index building, using memory sort fallback: drama={drama_name}", flush=True)
            # Fallback to memory sorting
            return _find_latest_ready_job_fallback(drama_name, request_id)
        else:
            # Other errors: log and return None
            logger.exception(
                "[RELAY] Query ready job failed",
                extra={
                    "request_id": request_id,
                    "drama_name": drama_name,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            print(f"[RELAY-{request_id or 'N/A'}] ❌ Query ready job failed: drama={drama_name}, error={exc}", flush=True)
            return None, None


def _find_latest_ready_job_fallback(drama_name: str, request_id: str | None = None) -> Tuple[str, Dict[str, Any]] | Tuple[None, None]:
    """Fallback method using memory sorting when index is not ready.
    
    This method fetches all jobs for the drama_name and sorts in memory.
    Used when the composite index is still building.
    """
    firestore_client = _get_firestore_client()
    
    # Query without order_by (no index required)
    query = (
        firestore_client.collection(FIRESTORE_COLLECTION)
        .where("drama_name", "==", drama_name)
        .limit(50)  # Fetch more to ensure we get the latest
    )
    
    try:
        candidates = []
        for snapshot in query.stream():
            data = snapshot.to_dict() or {}
            if not data:
                continue
            transfer_completed = bool(data.get("transfer_completed"))
            stage = data.get("stage")
            if transfer_completed and (stage == 1 or stage is None):
                updated_at = data.get("updated_at")
                candidates.append((snapshot.id, data, updated_at))
        
        if not candidates:
            logger.warning(
                "[RELAY] No ready job found (memory sort fallback)",
                extra={
                    "request_id": request_id,
                    "drama_name": drama_name,
                    "candidates_count": len(candidates),
                }
            )
            print(f"[RELAY-{request_id or 'N/A'}] ⚠️  No ready job found (memory sort): drama={drama_name}, candidates={len(candidates)}", flush=True)
            return None, None
        
        # Sort by updated_at descending in memory
        candidates.sort(key=lambda x: x[2] or "", reverse=True)
        job_id, job_data, _ = candidates[0]
        
        logger.info(
            "[RELAY] Ready job found (memory sort fallback)",
            extra={
                "request_id": request_id,
                "job_id": job_id,
                "drama_name": drama_name,
                "updated_at": str(job_data.get("updated_at")),
            }
        )
        print(f"[RELAY-{request_id or 'N/A'}] ✅ Found ready job (memory sort): job_id={job_id}, drama={drama_name}", flush=True)
        return job_id, job_data
    
    except Exception as exc:
        logger.exception(
            "[RELAY] Memory sort fallback failed",
            extra={
                "request_id": request_id,
                "drama_name": drama_name,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
        )
        print(f"[RELAY-{request_id or 'N/A'}] ❌ Memory sort fallback failed: drama={drama_name}, error={exc}", flush=True)
        return None, None


def _trigger_local_worker(job_id: str) -> str:
    env = os.environ.copy()
    env["JOB_ID"] = job_id
    env.setdefault("PYTHONPATH", os.getcwd())
    process = subprocess.Popen(
        [sys.executable, "-m", "app.workers.process.main"],
        env=env,
        cwd=os.getcwd(),
    )
    logger.info("🚀 [DEV] 本地启动 Process Worker，PID=%s, JOB_ID=%s", process.pid, job_id)
    return f"local-process:{process.pid}"


def _trigger_cloud_run_job(job_id: str, drama_name: str) -> str:
    """Trigger Cloud Run Job with sharding support.
    
    This function:
    1. Discovers file pairs to calculate total_files
    2. Calculates task_count = min(total_files, 100)
    3. Updates Firestore job document with total_files, processed_files=0, failed_files=0
    4. Triggers Cloud Run Job with task_count in overrides
    """
    job_name = settings.process_job_name.strip()
    if not job_name:
        raise RuntimeError("PROCESSOR_JOB_NAME 未配置，无法触发 Cloud Run Job")

    # Step 1: Discover file pairs to calculate total_files
    try:
        pairs = discover_file_pairs(
            drama_name=drama_name,
            source_bucket=settings.pipeline_gcs_source_bucket,
        )
        total_files = len(pairs)
        logger.info(
            "📊 Discovered %d file pairs for drama=%s",
            total_files,
            drama_name,
        )
    except Exception as exc:
        # If discovery fails, log warning but continue (worker will set total_files)
        logger.warning(
            "⚠️ Failed to discover file pairs for drama=%s: %s. Worker will set total_files.",
            drama_name,
            exc,
        )
        total_files = None

    # Step 2: Calculate task_count
    # Strategy: Limit each Task to max 3 files to prevent timeout
    # For >100 files: task_count = ceil(total / 3), capped at 100
    # For <=100 files: task_count = total_files (1:1 mapping)
    task_count = None
    if total_files is not None and total_files > 0:
        import math
        if total_files <= 100:
            # Small batch: 1:1 mapping
            task_count = total_files
        else:
            # Large batch: limit each Task to max 3 files
            # task_count = ceil(total / 3), but cap at 100 to prevent DB pressure
            task_count = min(math.ceil(total_files / 3), 100)
        logger.info(
            "📊 Calculated task_count=%d for total_files=%d (max 3 files per task)",
            task_count,
            total_files,
        )

    # Step 3: Update Firestore job document before triggering
    firestore_client = _get_firestore_client()
    job_ref = firestore_client.collection(FIRESTORE_COLLECTION).document(job_id)
    
    update_data = {
        "updated_at": SERVER_TIMESTAMP,
    }
    
    # Set total_files if we have it
    if total_files is not None:
        update_data["total_files"] = total_files
    
    # Ensure processed_files and failed_files are initialized
    job_snapshot = job_ref.get()
    if job_snapshot.exists:
        job_data = job_snapshot.to_dict() or {}
        if "processed_files" not in job_data:
            update_data["processed_files"] = 0
        if "failed_files" not in job_data:
            update_data["failed_files"] = 0
    else:
        # Job doesn't exist, this shouldn't happen but handle gracefully
        logger.warning("⚠️ Job document %s does not exist", job_id)
        update_data["processed_files"] = 0
        update_data["failed_files"] = 0
    
    job_ref.update(update_data)
    logger.info(
        "📝 Updated Firestore job document: total_files=%s, processed_files=0, failed_files=0",
        total_files,
    )

    # Step 4: Prepare environment variables
    env_vars = [
        {"name": "JOB_ID", "value": job_id},
        {"name": "DRAMA_NAME", "value": drama_name},
    ]
    if settings.pipeline_default_token_ref:
        env_vars.append(
            {"name": "PIPELINE_DEFAULT_TOKEN_REF", "value": settings.pipeline_default_token_ref}
        )

    # Step 5: Build payload with task_count if available
    # Note: taskCount is set via overrides_kwargs, env vars via ContainerOverride
    
    # Step 6: Trigger Cloud Run Job using run_v2 API
    jobs_client = _get_jobs_client()
    
    # Convert payload to run_v2 format
    env_vars_v2 = [
        run_v2.EnvVar(name=env["name"], value=env["value"])
        for env in env_vars
    ]
    
    overrides_kwargs = {
        "container_overrides": [
            run_v2.RunJobRequest.Overrides.ContainerOverride(
                env=env_vars_v2  # Inject environment variables here
            ),
        ]
    }
    
    # Add task_count to overrides if available
    if task_count is not None:
        overrides_kwargs["task_count"] = task_count
    
    overrides = run_v2.RunJobRequest.Overrides(**overrides_kwargs)
    
    request = run_v2.RunJobRequest(
        name=job_name,
        overrides=overrides,
    )
    
    try:
        operation = jobs_client.run_job(request=request)
        op_name = getattr(getattr(operation, "operation", None), "name", None)
        logger.info(
            "✅ 已触发 Cloud Run Job %s (operation=%s, task_count=%s)",
            job_name,
            op_name,
            task_count,
        )
        return op_name or "unknown-operation"
    except Exception as exc:
        raise RuntimeError(f"Cloud Run Jobs API 调用失败：{exc}") from exc


@router.post("/event", summary="Eventarc relay endpoint", status_code=200)
async def relay_event(request: Request) -> Dict[str, Any]:
    """Relay GCS finalized events (_PROCESS_NOW) to the processor job.
    
    Supports multiple event formats:
    - CloudEvents format: {"type": "...", "data": {"bucket": "...", "name": "..."}}
    - Pub/Sub format: {"message": {"data": "...", "attributes": {...}}}
    - Direct format: {"bucket": "...", "name": "..."}
    """
    import uuid
    import json
    import base64
    request_id = str(uuid.uuid4())[:8]
    
    try:
        payload = await request.json()
        
        # Log full payload for debugging
        logger.info(
            "[RELAY] Full Eventarc payload received",
            extra={
                "request_id": request_id,
                "full_payload": json.dumps(payload, default=str),
            }
        )
        print(f"[RELAY-{request_id}] 📋 Full payload: {json.dumps(payload, default=str)[:1000]}", flush=True)
        
        # Try to extract event data from different formats
        event_type = ""
        bucket = None
        object_name = None
        
        # Format 1: CloudEvents format
        if "type" in payload and "data" in payload:
            event_type = payload.get("type", "")
            data = payload.get("data") or {}
            bucket = data.get("bucket")
            object_name = data.get("name")
        
        # Format 2: Pub/Sub format (message.data is base64 encoded)
        elif "message" in payload:
            message = payload.get("message", {})
            attributes = message.get("attributes", {})
            event_type = attributes.get("eventType", "")
            bucket = attributes.get("bucketId")
            object_name = attributes.get("objectId")
            
            # If object_name is in data, decode it
            if not object_name and "data" in message:
                try:
                    decoded_data = base64.b64decode(message["data"]).decode("utf-8")
                    data_obj = json.loads(decoded_data)
                    bucket = data_obj.get("bucket") or bucket
                    object_name = data_obj.get("name") or object_name
                except Exception:
                    pass
        
        # Format 3: Direct format
        elif "bucket" in payload or "name" in payload:
            bucket = payload.get("bucket")
            object_name = payload.get("name")
        
        # Format 4: Check if it's in the request body directly
        else:
            # Try to find bucket and name in the payload recursively
            def find_in_dict(d, key):
                if isinstance(d, dict):
                    if key in d:
                        return d[key]
                    for v in d.values():
                        result = find_in_dict(v, key)
                        if result:
                            return result
                elif isinstance(d, list):
                    for item in d:
                        result = find_in_dict(item, key)
                        if result:
                            return result
                return None
            
            bucket = find_in_dict(payload, "bucket") or find_in_dict(payload, "bucketId")
            object_name = find_in_dict(payload, "name") or find_in_dict(payload, "objectId") or find_in_dict(payload, "object")

        # Enhanced logging with structured data and stdout
        logger.info(
            "[RELAY] Eventarc event received",
            extra={
                "request_id": request_id,
                "event_type": event_type,
                "bucket": bucket,
                "object_name": object_name,
                "endpoint": "/api/relay/event",
            }
        )
        print(f"[RELAY-{request_id}] 📬 Eventarc event received: type={event_type}, bucket={bucket}, name={object_name}", flush=True)

        if not object_name or not object_name.endswith(PROCESS_SIGNAL_SUFFIX):
            logger.info(
                "[RELAY] Non-target object, ignoring",
                extra={
                    "request_id": request_id,
                    "object_name": object_name,
                    "reason": "object_not_matching",
                }
            )
            print(f"[RELAY-{request_id}] ⏭️  Non-target object, ignoring: {object_name}", flush=True)
            return {"status": "ignored", "reason": "object_not_matching", "request_id": request_id}

        drama_name = _extract_drama_name(object_name)
        if not drama_name:
            logger.warning(
                "[RELAY] Failed to extract drama_name",
                extra={
                    "request_id": request_id,
                    "object_name": object_name,
                    "reason": "missing_drama_name",
                }
            )
            print(f"[RELAY-{request_id}] ⚠️  Failed to extract drama_name from: {object_name}", flush=True)
            return {"status": "ignored", "reason": "missing_drama_name", "request_id": request_id}

        logger.info(
            "[RELAY] Extracted drama_name",
            extra={
                "request_id": request_id,
                "drama_name": drama_name,
                "object_name": object_name,
            }
        )
        print(f"[RELAY-{request_id}] 📝 Extracted drama_name: {drama_name}", flush=True)

        # Step: Find latest ready job
        logger.info(
            "[RELAY] Searching for ready job",
            extra={
                "request_id": request_id,
                "drama_name": drama_name,
            }
        )
        print(f"[RELAY-{request_id}] 🔍 Searching for ready job: drama={drama_name}", flush=True)
        
        job_id, job_doc = _find_latest_ready_job(drama_name, request_id)
        if not job_id:
            logger.warning(
                "[RELAY] No ready job found",
                extra={
                    "request_id": request_id,
                    "drama_name": drama_name,
                    "reason": "job_not_found",
                }
            )
            print(f"[RELAY-{request_id}] ⚠️  No ready job found for drama={drama_name}", flush=True)
            return {"status": "ignored", "reason": "job_not_found", "drama_name": drama_name, "request_id": request_id}

        logger.info(
            "[RELAY] Ready job found",
            extra={
                "request_id": request_id,
                "job_id": job_id,
                "drama_name": drama_name,
            }
        )
        print(f"[RELAY-{request_id}] 🎯 Found ready job: job_id={job_id}, drama={drama_name}", flush=True)

        # Step 1: Acquire job slot (with transaction protection)
        logger.info(
            "[RELAY] Acquiring job slot",
            extra={
                "request_id": request_id,
                "job_id": job_id,
                "drama_name": drama_name,
            }
        )
        print(f"[RELAY-{request_id}] 🔐 Acquiring job slot: job_id={job_id}", flush=True)
        
        concurrency_service = ConcurrencyService()
        can_start, slot_message = concurrency_service.acquire_job_slot(job_id)
        
        logger.info(
            "[RELAY] Job slot acquisition result",
            extra={
                "request_id": request_id,
                "job_id": job_id,
                "can_start": can_start,
                "slot_message": slot_message,
            }
        )
        print(f"[RELAY-{request_id}] 🔐 Slot acquisition result: can_start={can_start}, message={slot_message}", flush=True)
        
        if not can_start:
            # Job is queued, return immediately
            logger.info(
                "[RELAY] Job queued",
                extra={
                    "request_id": request_id,
                    "job_id": job_id,
                    "drama_name": drama_name,
                    "slot_message": slot_message,
                    "status": "queued",
                }
            )
            print(f"[RELAY-{request_id}] ⏳ Job queued: job_id={job_id}, {slot_message}", flush=True)
            return {
                "status": "queued",
                "job_id": job_id,
                "drama_name": drama_name,
                "message": slot_message,
                "request_id": request_id,
            }
        
        # Step 2: Job can start, trigger it
        logger.info(
            "[RELAY] Triggering Cloud Run Job",
            extra={
                "request_id": request_id,
                "job_id": job_id,
                "drama_name": drama_name,
                "env": settings.app_env,
            }
        )
        print(f"[RELAY-{request_id}] 🚀 Triggering Cloud Run Job: job_id={job_id}, env={settings.app_env}", flush=True)
        
        try:
            if settings.app_env == "development":
                operation = _trigger_local_worker(job_id)
            else:
                operation = _trigger_cloud_run_job(job_id, drama_name)
            
            logger.info(
                "[RELAY] Cloud Run Job triggered successfully",
                extra={
                    "request_id": request_id,
                    "job_id": job_id,
                    "drama_name": drama_name,
                    "operation": operation,
                    "status": "triggered",
                }
            )
            print(f"[RELAY-{request_id}] ✅ Cloud Run Job triggered: job_id={job_id}, operation={operation}", flush=True)
            
            result = {
                "status": "triggered",
                "job_id": job_id,
                "operation": operation,
                "drama_name": drama_name,
                "message": slot_message,
                "request_id": request_id,
            }
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "[RELAY] Failed to trigger Cloud Run Job",
                extra={
                    "request_id": request_id,
                    "job_id": job_id,
                    "drama_name": drama_name,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            print(f"[RELAY-{request_id}] ❌ Failed to trigger Cloud Run Job: job_id={job_id}, error={exc}", flush=True)
            
            # Release slot on error and try to trigger next job
            try:
                logger.info(
                    "[RELAY] Releasing slot and triggering next job after error",
                    extra={
                        "request_id": request_id,
                        "job_id": job_id,
                    }
                )
                print(f"[RELAY-{request_id}] 🔓 Releasing slot and triggering next job after error", flush=True)
                concurrency_service = ConcurrencyService()
                triggered = concurrency_service.release_and_trigger_next(job_id)
                logger.info(
                    "[RELAY] Slot released and next job trigger result",
                    extra={
                        "request_id": request_id,
                        "job_id": job_id,
                        "next_job_triggered": triggered,
                    }
                )
                print(f"[RELAY-{request_id}] 🔓 Slot released, next job triggered: {triggered}", flush=True)
            except Exception as release_exc:
                logger.exception(
                    "[RELAY] Failed to release slot and trigger next job",
                    extra={
                        "request_id": request_id,
                        "job_id": job_id,
                        "error": str(release_exc),
                        "error_type": type(release_exc).__name__,
                    }
                )
                print(f"[RELAY-{request_id}] ❌ Failed to release slot: {release_exc}", flush=True)
            
            result = {
                "status": "error",
                "job_id": job_id,
                "drama_name": drama_name,
                "message": str(exc),
                "request_id": request_id,
            }

        # Always return 200 to avoid Eventarc retry storm
        logger.info(
            "[RELAY] Request completed",
            extra={
                "request_id": request_id,
                "job_id": job_id,
                "drama_name": drama_name,
                "result_status": result.get("status"),
            }
        )
        print(f"[RELAY-{request_id}] ✅ Request completed: status={result.get('status')}", flush=True)
        return result
        
    except Exception as exc:
        logger.exception(
            "[RELAY] Unexpected error in relay_event",
            extra={
                "request_id": request_id,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
        )
        print(f"[RELAY-{request_id}] ❌ Unexpected error: {exc}", flush=True)
        return {
            "status": "error",
            "message": str(exc),
            "request_id": request_id,
        }

