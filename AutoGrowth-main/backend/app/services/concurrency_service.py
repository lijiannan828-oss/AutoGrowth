import logging
from typing import Tuple, List, Set, Dict, Any, Optional
from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from google.cloud import run_v2

from app.core.config import settings
from app.core.firestore import get_firestore_client
from app.services.pipeline_discovery_service import discover_file_pairs

logger = logging.getLogger(__name__)

CONCURRENCY_CONTROL_COLLECTION = "system_config"
CONCURRENCY_CONTROL_DOC = "concurrency_control"
FIRESTORE_COLLECTION = "pipeline_jobs"
# Job timeout in seconds (3 hours + buffer)
JOB_TIMEOUT_SECONDS = 3.5 * 3600 

class ConcurrencyService:
    def __init__(self):
        self.firestore_client = get_firestore_client()
        self.control_ref = self.firestore_client.collection(CONCURRENCY_CONTROL_COLLECTION).document(CONCURRENCY_CONTROL_DOC)
        self._jobs_client: Optional[run_v2.JobsClient] = None
        self._executions_client: Optional[run_v2.ExecutionsClient] = None
    
    def _get_jobs_client(self) -> run_v2.JobsClient:
        """Get Cloud Run Jobs client (lazy initialization)."""
        if self._jobs_client is None:
            self._jobs_client = run_v2.JobsClient()
        return self._jobs_client

    def _get_executions_client(self) -> run_v2.ExecutionsClient:
        """Get Cloud Run Executions client (lazy initialization)."""
        if self._executions_client is None:
            self._executions_client = run_v2.ExecutionsClient()
        return self._executions_client

    def _check_cloud_run_execution_status(self, job_id: str) -> Optional[str]:
        """Check Cloud Run Job execution status for a given job_id.
        
        This checks if there's a recent Cloud Run Job execution that matches this job_id.
        Returns the execution status (SUCCEEDED, FAILED, CANCELLED, RUNNING, etc.) or None.
        
        Args:
            job_id: The Firestore job document ID
            
        Returns:
            Optional[str]: Execution status, or None if not found or error
        """
        try:
            executions_client = self._get_executions_client()
            logger.debug("Checking Cloud Run execution status for job_id=%s", job_id)
            job_name = settings.process_job_name.strip()
            
            # Extract job name from full path if needed
            # Full path format: projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}
            # We need just the job name for the API call
            if "/jobs/" in job_name:
                job_name = job_name.split("/jobs/")[-1]
            
            # Fallback to default job name if not configured
            if not job_name:
                job_name = "drama-processor-job"
            
            # Get project_id and region
            import os
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or "fleet-blend-469520-n7"
            region = os.environ.get("GCP_REGION") or "us-central1"
            
            # List recent executions (increase page_size to 50 to catch older executions)
            parent = f"projects/{project_id}/locations/{region}/jobs/{job_name}"
            request = run_v2.ListExecutionsRequest(parent=parent, page_size=50)
            response = executions_client.list_executions(request=request)
            
            # Find execution that matches our job_id
            # We match by getting execution details and checking JOB_ID env var
            # Note: list_executions() returns Execution objects without template details
            # We need to call get_execution() to access template.containers
            for execution in response.executions:
                try:
                    # Get full execution details to access template
                    execution_name = execution.name if hasattr(execution, 'name') else None
                    if not execution_name:
                        continue
                    
                    # Get execution details (this includes template with containers)
                    exec_details = executions_client.get_execution(name=execution_name)
                    
                    # Check if execution has JOB_ID env var matching our job_id
                    containers = exec_details.template.containers if hasattr(exec_details, 'template') and exec_details.template else []
                    for container in containers:
                        env_vars = container.env if hasattr(container, 'env') else []
                        for env_var in env_vars:
                            if env_var.name == "JOB_ID" and env_var.value == job_id:
                                # Found matching execution
                                logger.debug("Found matching execution: %s", execution_name)
                                # Check execution status (use exec_details which has all status info)
                                # Check conditions for final status
                                conditions = exec_details.conditions if hasattr(exec_details, 'conditions') else []
                                logger.debug("Execution has %d conditions", len(conditions))
                                for condition in conditions:
                                    # Use type_ (not type) for condition type
                                    cond_type = getattr(condition, 'type_', None)
                                    if cond_type == "Completed":
                                        # Check message for cancellation or timeout
                                        message = getattr(condition, 'message', '') or ''
                                        if 'Cancelled' in message or 'cancelled' in message.lower():
                                            logger.debug("Execution cancelled: %s", message)
                                            return "CANCELLED"
                                        elif 'DeadlineExceeded' in message or 'timeout' in message.lower():
                                            logger.debug("Execution timed out: %s", message)
                                            return "TIMEOUT"
                                        else:
                                            # Check if succeeded or failed
                                            succeeded = exec_details.succeeded_count if hasattr(exec_details, 'succeeded_count') else 0
                                            failed = exec_details.failed_count if hasattr(exec_details, 'failed_count') else 0
                                            if succeeded > 0 and failed == 0:
                                                return "SUCCEEDED"
                                            elif failed > 0:
                                                return "FAILED"
                                            else:
                                                return "COMPLETED"
                                # Check if still running
                                running = exec_details.running_count if hasattr(exec_details, 'running_count') else 0
                                if running > 0:
                                    return "RUNNING"
                                # Check if pending
                                pending = exec_details.pending_count if hasattr(exec_details, 'pending_count') else 0
                                if pending > 0:
                                    return "PENDING"
                                # If no conditions and no running/pending, might be completed
                                return "COMPLETED"
                except Exception as e:
                    logger.debug("Error checking execution %s: %s", execution.name if hasattr(execution, 'name') else 'unknown', e)
                    continue
            
            logger.debug("No matching execution found for job_id=%s", job_id)
            return None
        except Exception as exc:
            logger.warning("Failed to check Cloud Run execution status for job_id=%s: %s", job_id, exc, exc_info=True)
            return None
    
    def _cleanup_completed_jobs(self) -> int:
        """Clean up completed or timed-out jobs from the running count.
        
        Checks all jobs in 'running_job_ids' list AND all PROCESSING jobs in Firestore.
        Removes them if:
        1. Job status is SUCCEEDED or FAILED
        2. Job document doesn't exist
        3. Job updated_at is older than timeout (Zombie job)
        4. Cloud Run Job execution is CANCELLED or TIMEOUT (manually stopped)
        5. Cloud Run Job execution is not RUNNING but Firestore status is PROCESSING (stale state)
        """
        # Get current running jobs
        snapshot = self.control_ref.get()
        if not snapshot.exists:
            # If control document doesn't exist, initialize it
            self.control_ref.set({
                "max_concurrent_jobs": settings.max_concurrent_jobs,
                "running_jobs": 0,
                "running_job_ids": [],
                "queue": [],
                "updated_at": SERVER_TIMESTAMP,
            })
            running_job_ids = set()
        else:
            data = snapshot.to_dict() or {}
            running_job_ids = set(data.get("running_job_ids", []))
        
        # CRITICAL FIX: Also check all PROCESSING jobs in Firestore
        # This handles the case where running_job_ids is empty but there are stale PROCESSING jobs
        jobs_collection = self.firestore_client.collection(FIRESTORE_COLLECTION)
        processing_jobs = list(jobs_collection.where("status", "==", "PROCESSING").stream())
        
        # Add PROCESSING jobs to the set to check
        processing_job_ids = {job.id for job in processing_jobs}
        all_job_ids_to_check = running_job_ids | processing_job_ids
        
        if not all_job_ids_to_check:
            return 0
        
        cleaned_count = 0
        to_remove = set()
        
        import time
        now = time.time()

        for job_id in list(all_job_ids_to_check):
            job_snapshot = jobs_collection.document(job_id).get()
            
            # Case 1: Job document missing
            if not job_snapshot.exists:
                to_remove.add(job_id)
                cleaned_count += 1
                logger.warning("🧹 Cleaning up missing job: %s", job_id)
                continue
            
            job_data = job_snapshot.to_dict() or {}
            status = (job_data.get("status") or "").upper()
            updated_at = job_data.get("updated_at")
            
            # Case 2: Job completed (Firestore status)
            if status in ("SUCCEEDED", "FAILED", "COMPLETE"):
                to_remove.add(job_id)
                cleaned_count += 1
                logger.info("🧹 Cleaning up completed job: %s (status=%s)", job_id, status)
                continue
            
            # Case 2.5: Job is QUEUED but in running_job_ids
            # It might be a zombie (failed to start) OR just starting up
            # We must be careful not to kill a job that is just starting
            if status == "QUEUED":
                # Check if it's been queued for too long (e.g. > 5 minutes)
                is_zombie_queued = False
                try:
                    ts = updated_at.timestamp() if hasattr(updated_at, 'timestamp') else 0
                    # If queued for > 5 minutes, assume it's stuck/failed
                    if now - ts > 300:
                        is_zombie_queued = True
                        logger.warning("🧟 Job %s has been QUEUED for > 5 mins, treating as ZOMBIE", job_id)
                except Exception:
                    # If timestamp invalid, assume zombie
                    is_zombie_queued = True
                
                if is_zombie_queued:
                    to_remove.add(job_id)
                    cleaned_count += 1
                    logger.warning("🧹 Cleaning up STUCK QUEUED job: %s", job_id)
                    # Update job status to FAILED
                    try:
                        job_ref = self.firestore_client.collection(FIRESTORE_COLLECTION).document(job_id)
                        job_ref.update({
                            "status": "FAILED",
                            "progress": "任务启动超时（停留在QUEUED状态过久，已清理）",
                            "updated_at": SERVER_TIMESTAMP,
                        })
                    except Exception as e:
                        logger.warning("⚠️ Failed to update QUEUED job %s status: %s", job_id, e)
                else:
                    # It's a fresh QUEUED job, leave it alone! It counts as running.
                    logger.info("⏳ Job %s is QUEUED but fresh (< 5 mins), counting as RUNNING", job_id)
                
                continue
            
            # Case 2.6: Check Cloud Run Job execution status for PROCESSING jobs
            # This handles cases where job was manually cancelled in GCP console
            if status == "PROCESSING":
                execution_status = self._check_cloud_run_execution_status(job_id)
                if execution_status:
                    if execution_status in ("CANCELLED", "TIMEOUT"):
                        # Job was cancelled or timed out in Cloud Run, but Firestore still shows PROCESSING
                        to_remove.add(job_id)
                        cleaned_count += 1
                        logger.warning(
                            "🧹 Cleaning up cancelled/timed-out job: %s (Firestore=PROCESSING, CloudRun=%s)",
                            job_id,
                            execution_status
                        )
                        # Update Firestore job document to reflect actual status
                        try:
                            job_ref = self.firestore_client.collection(FIRESTORE_COLLECTION).document(job_id)
                            job_ref.update({
                                "status": "FAILED",
                                "progress": f"任务已在 GCP 后台被取消或超时 ({execution_status})",
                                "updated_at": SERVER_TIMESTAMP,
                            })
                            logger.info(
                                "[CONCURRENCY] Updated job status to FAILED (cancelled/timeout)",
                                extra={"job_id": job_id, "execution_status": execution_status}
                            )
                        except Exception as e:
                            logger.warning("⚠️ Failed to update job %s status: %s", job_id, e)
                        continue
                    elif execution_status not in ("RUNNING", "PENDING"):
                        # Execution is not running but Firestore shows PROCESSING (stale state)
                        # This could be SUCCEEDED, FAILED, or other final states
                        to_remove.add(job_id)
                        cleaned_count += 1
                        logger.warning(
                            "🧹 Cleaning up stale PROCESSING job: %s (Firestore=PROCESSING, CloudRun=%s)",
                            job_id,
                            execution_status
                        )
                        # Update Firestore job document
                        try:
                            job_ref = self.firestore_client.collection(FIRESTORE_COLLECTION).document(job_id)
                            firestore_status = "SUCCEEDED" if execution_status == "SUCCEEDED" else "FAILED"
                            job_ref.update({
                                "status": firestore_status,
                                "progress": f"任务执行状态: {execution_status}",
                                "updated_at": SERVER_TIMESTAMP,
                            })
                            logger.info(
                                "[CONCURRENCY] Updated stale PROCESSING job",
                                extra={"job_id": job_id, "execution_status": execution_status, "firestore_status": firestore_status}
                            )
                        except Exception as e:
                            logger.warning("⚠️ Failed to update job %s status: %s", job_id, e)
                        continue

            # Case 3: Job timed out (Zombie)
            if updated_at:
                # Handle Firestore Timestamp
                try:
                    ts = updated_at.timestamp() if hasattr(updated_at, 'timestamp') else 0
                    if now - ts > JOB_TIMEOUT_SECONDS:
                        to_remove.add(job_id)
                        cleaned_count += 1
                        logger.warning("🧟 Cleaning up ZOMBIE job: %s (last_update=%.1f hours ago)", job_id, (now - ts)/3600)
                        # Optionally: Mark job as FAILED in Firestore?
                        # For now, just release the slot.
                except Exception as e:
                    logger.warning("⚠️ Error checking timestamp for job %s: %s", job_id, e)

        if to_remove:
            # Update control document
            # We must read-modify-write carefully, but since this is 'cleanup', 
            # strict atomicity against concurrent 'acquire' is handled by acquire's transaction.
            # However, to be safe, let's use a transaction or array_remove if possible.
            # Here we just update the whole list for simplicity, assuming single-threaded cleanup usually.
            # Better: Use array_remove in a transaction? No, array_remove limits 10 elements.
            
            # Re-read control document to get current state
            snapshot = self.control_ref.get()
            if snapshot.exists:
                data = snapshot.to_dict() or {}
                running_job_ids = set(data.get("running_job_ids", []))
            else:
                running_job_ids = set()
            
            # Remove cleaned jobs from running_job_ids
            running_job_ids.difference_update(to_remove)
            
            # Ensure max_concurrent_jobs is set
            max_concurrent = data.get("max_concurrent_jobs") if snapshot.exists else settings.max_concurrent_jobs
            if max_concurrent is None:
                max_concurrent = settings.max_concurrent_jobs
            
            self.control_ref.set({
                "max_concurrent_jobs": max_concurrent,
                "running_jobs": len(running_job_ids),
                "running_job_ids": list(running_job_ids),
                "queue": data.get("queue", []) if snapshot.exists else [],
                "updated_at": SERVER_TIMESTAMP,
            }, merge=True)
            
            # Update job documents to clear stale progress messages
            # This ensures that cleaned jobs don't show outdated queue positions
            for job_id in to_remove:
                try:
                    job_ref = self.firestore_client.collection(FIRESTORE_COLLECTION).document(job_id)
                    job_snapshot = job_ref.get()
                    if job_snapshot.exists:
                        job_data = job_snapshot.to_dict() or {}
                        current_status = (job_data.get("status") or "").upper()
                        
                        # Update QUEUED status to FAILED if job was cleaned up
                        if current_status == "QUEUED":
                            job_ref.update({
                                "status": "FAILED",
                                "progress": "任务已超时或被清理，请重新触发",
                                "updated_at": SERVER_TIMESTAMP,
                            })
                            logger.info(
                                "[CONCURRENCY] Updated stale QUEUED job progress",
                                extra={"job_id": job_id}
                            )
                except Exception as exc:
                    logger.warning(
                        "[CONCURRENCY] Failed to update job document during cleanup",
                        extra={
                            "job_id": job_id,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        }
                    )
            
        return cleaned_count

    def acquire_job_slot(self, job_id: str) -> Tuple[bool, str]:
        """Acquire a job slot using Firestore transaction.
        
        Returns:
            (can_start, message)
        """
        # 1. Best-effort cleanup before transaction
        try:
            cleaned_count = self._cleanup_completed_jobs()
            if cleaned_count > 0:
                logger.info(
                    "[CONCURRENCY] Cleaned up completed jobs before acquire",
                    extra={
                        "job_id": job_id,
                        "cleaned_count": cleaned_count,
                    }
                )
                print(f"[CONCURRENCY] 🧹 Cleaned up {cleaned_count} completed jobs before acquire: job_id={job_id}", flush=True)
        except Exception as exc:
            logger.warning(
                "[CONCURRENCY] Cleanup failed before acquire",
                extra={
                    "job_id": job_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            print(f"[CONCURRENCY] ⚠️ Cleanup failed before acquire: job_id={job_id}, error={exc}", flush=True)

        max_concurrent = settings.max_concurrent_jobs
        
        logger.info(
            "[CONCURRENCY] Starting acquire_job_slot transaction",
            extra={
                "job_id": job_id,
                "max_concurrent": max_concurrent,
            }
        )
        print(f"[CONCURRENCY] 🔐 Starting acquire_job_slot: job_id={job_id}, max_concurrent={max_concurrent}", flush=True)
        
        # CRITICAL FIX: Query PROCESSING jobs OUTSIDE the transaction
        # Firestore transactions cannot execute queries (where().stream())
        # They can only read/write documents (get(), set(), update(), delete())
        # So we query before the transaction and pass the result via closure
        try:
            jobs_collection = self.firestore_client.collection(FIRESTORE_COLLECTION)
            processing_jobs_query = jobs_collection.where("status", "==", "PROCESSING")
            processing_jobs = list(processing_jobs_query.stream())
            processing_job_ids = {job.id for job in processing_jobs}
            logger.info(
                "[CONCURRENCY] Queried PROCESSING jobs outside transaction",
                extra={
                    "job_id": job_id,
                    "processing_count": len(processing_job_ids),
                    "processing_job_ids": list(processing_job_ids),
                }
            )
            print(f"[CONCURRENCY] 📋 Queried {len(processing_job_ids)} PROCESSING jobs outside transaction: {list(processing_job_ids)}", flush=True)
        except Exception as exc:
            logger.warning(
                "[CONCURRENCY] Failed to query PROCESSING jobs, using empty set",
                extra={
                    "job_id": job_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            print(f"[CONCURRENCY] ⚠️ Failed to query PROCESSING jobs: {exc}, using empty set", flush=True)
            processing_job_ids = set()
        
        @firestore.transactional
        def _acquire_transaction(transaction):
            snapshot = self.control_ref.get(transaction=transaction)
            
            if snapshot.exists:
                data = snapshot.to_dict() or {}
                running_job_ids = set(data.get("running_job_ids", []))
                queue = data.get("queue", [])
            else:
                running_job_ids = set()
                queue = []
            
            # CRITICAL FIX: Verify running_job_ids actually have PROCESSING status
            # Some jobs in running_job_ids might have already completed but not cleaned up yet
            # We need to check their actual status in Firestore within the transaction
            verified_running_job_ids = set()
            jobs_collection = self.firestore_client.collection(FIRESTORE_COLLECTION)
            
            # Use different variable name to avoid shadowing the outer job_id
            for running_job_id in running_job_ids:
                job_ref = jobs_collection.document(running_job_id)
                job_snapshot = job_ref.get(transaction=transaction)
                if job_snapshot.exists:
                    job_data = job_snapshot.to_dict() or {}
                    status = (job_data.get("status") or "").upper()
                    # CRITICAL FIX: Consider ANY non-terminal status as running
                    # STICT LOCKING: If it's in running_job_ids, it COUNTS, unless it's explicitly finished.
                    # We COUNT "QUEUED", "PENDING", "PROCESSING", or even None (just created)
                    # We ONLY exclude explicit terminal states: SUCCEEDED, FAILED, COMPLETED, CANCELLED
                    if status not in ("SUCCEEDED", "FAILED", "COMPLETED", "CANCELLED", "RESOLVED"):
                        verified_running_job_ids.add(running_job_id)
                    else:
                        # Log that we are ignoring a finished job that is still in the list (will be cleaned up later)
                        logger.info(f"[CONCURRENCY] Ignoring finished job in running list: {running_job_id} (status={status})")
                else:
                    # If document missing but in list, we must assume it's running or zombie
                    # To be safe against race conditions, we COUNT it until cleanup removes it
                    logger.warning(f"[CONCURRENCY] Job doc missing but in running list: {running_job_id}")
                    verified_running_job_ids.add(running_job_id)
            
            # CRITICAL: Also verify PROCESSING jobs queried outside transaction
            # Some PROCESSING jobs might be stale (completed but status not updated)
            # We need to verify them within the transaction to get accurate count
            verified_processing_job_ids = set()
            for processing_job_id in processing_job_ids:
                job_ref = jobs_collection.document(processing_job_id)
                job_snapshot = job_ref.get(transaction=transaction)
                if job_snapshot.exists:
                    job_data = job_snapshot.to_dict() or {}
                    status = (job_data.get("status") or "").upper()
                    # For queried jobs, we count them if they are NOT finished
                    # Explicitly include QUEUED here too just in case
                    if status not in ("SUCCEEDED", "FAILED", "COMPLETED", "CANCELLED", "RESOLVED"):
                        verified_processing_job_ids.add(processing_job_id)
            
            # CRITICAL FIX: Due to Firestore eventual consistency, the query outside transaction
            # might not see jobs that were just updated to PROCESSING. 
            # The query might return 0 PROCESSING jobs even though there are jobs in running_job_ids
            # that are actually PROCESSING. We must use verified_running_job_ids as the source of truth
            # since it's verified within the transaction.
            
            # Merge verified sets - this gives us the accurate count of actually running jobs
            actual_running_job_ids = verified_running_job_ids | verified_processing_job_ids
            
            # CRITICAL: Use the union count, but ensure we don't underestimate
            # If verified_running_job_ids has jobs (verified in transaction), we must count them
            # This prevents bypassing concurrency control when query misses recently updated jobs
            # The union ensures we catch all PROCESSING jobs, whether in running_job_ids or query result
            running_count = len(actual_running_job_ids)
            
            # Safety check: if verified_running_job_ids has jobs but query returned empty,
            # we must trust verified_running_job_ids (it's verified in transaction, so it's accurate)
            # This is critical to prevent concurrent execution when query misses jobs due to eventual consistency
            if len(verified_running_job_ids) > 0 and len(processing_job_ids) == 0:
                # Query might have missed jobs due to eventual consistency
                # Trust verified_running_job_ids (verified in transaction) - it's the source of truth
                # This ensures we don't allow new jobs when there are already running jobs
                running_count = len(verified_running_job_ids)
                actual_running_job_ids = verified_running_job_ids
            
            logger.info(
                "[CONCURRENCY] Current concurrency state",
                extra={
                    "job_id": job_id,
                    "running_count": running_count,
                    "max_concurrent": max_concurrent,
                    "queue_size": len(queue),
                    "running_job_ids": list(running_job_ids),
                    "verified_running_job_ids": list(verified_running_job_ids),
                    "verified_processing_job_ids": list(verified_processing_job_ids),
                    "actual_running_job_ids": list(actual_running_job_ids),
                }
            )
            print(f"[CONCURRENCY] 📊 Current state: running={running_count}/{max_concurrent}, queue_size={len(queue)}", flush=True)
            print(f"[CONCURRENCY] 📊 Verified: running_job_ids={list(verified_running_job_ids)}, processing_jobs={list(verified_processing_job_ids)}, actual={list(actual_running_job_ids)}", flush=True)
            
            # Check logic - use actual_running_job_ids count
            if running_count < max_concurrent:
                # Pass! Can start this job
                # Add new job to running_job_ids (it will be verified on next acquire)
                running_job_ids.add(job_id)
                
                # Ensure max_concurrent_jobs is set
                if not snapshot.exists or "max_concurrent_jobs" not in (data if snapshot.exists else {}):
                    max_concurrent_to_store = max_concurrent
                else:
                    max_concurrent_to_store = data.get("max_concurrent_jobs", max_concurrent)
                
                # CRITICAL: Only store verified running jobs + the new job
                # Don't include unverified PROCESSING jobs that aren't in running_job_ids
                # This prevents zombie tasks from being added to running_job_ids
                updated_running_job_ids = list(running_job_ids)
                
                transaction.set(self.control_ref, {
                    "max_concurrent_jobs": max_concurrent_to_store,
                    "running_jobs": len(updated_running_job_ids),
                    "running_job_ids": updated_running_job_ids,
                    "queue": queue, # Keep queue as is
                    "updated_at": SERVER_TIMESTAMP
                }, merge=True)
                
                msg = f"Job slot acquired (running={len(running_job_ids)}/{max_concurrent})"
                logger.info(
                    "[CONCURRENCY] Job slot acquired",
                    extra={
                        "job_id": job_id,
                        "running_count": len(running_job_ids),
                        "max_concurrent": max_concurrent,
                        "message": msg,
                    }
                )
                print(f"[CONCURRENCY] ✅ Job slot acquired: job_id={job_id}, {msg}", flush=True)
                return True, msg
            else:
                # Queue it
                if job_id not in queue:
                    queue.append(job_id)
                    transaction.set(self.control_ref, {
                        "queue": queue,
                        "updated_at": SERVER_TIMESTAMP
                    }, merge=True)
                    pos = len(queue)
                    msg = f"Job queued (position={pos}, running={running_count}/{max_concurrent})"
                    logger.info(
                        "[CONCURRENCY] Job queued",
                        extra={
                            "job_id": job_id,
                            "queue_position": pos,
                            "running_count": running_count,
                            "max_concurrent": max_concurrent,
                            "message": msg,
                        }
                    )
                    print(f"[CONCURRENCY] ⏳ Job queued: job_id={job_id}, {msg}", flush=True)
                    return False, msg
                else:
                    pos = queue.index(job_id) + 1
                    msg = f"Job already in queue (position={pos})"
                    logger.info(
                        "[CONCURRENCY] Job already in queue",
                        extra={
                            "job_id": job_id,
                            "queue_position": pos,
                            "message": msg,
                        }
                    )
                    print(f"[CONCURRENCY] ⏳ Job already in queue: job_id={job_id}, {msg}", flush=True)
                    return False, msg

        transaction = self.firestore_client.transaction()
        try:
            result = _acquire_transaction(transaction)
            logger.info(
                "[CONCURRENCY] Acquire transaction completed",
                extra={
                    "job_id": job_id,
                    "can_start": result[0],
                    "message": result[1],
                }
            )
            print(f"[CONCURRENCY] ✅ Acquire transaction completed: job_id={job_id}, can_start={result[0]}, message={result[1]}", flush=True)
            return result
        except Exception as exc:
            logger.exception(
                "[CONCURRENCY] Transaction failed for acquire_job_slot",
                extra={
                    "job_id": job_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            print(f"[CONCURRENCY] ❌ Transaction failed: job_id={job_id}, error={exc}", flush=True)
            # CRITICAL: Don't fail-open! If transaction fails, we can't guarantee concurrency control
            # Instead, queue the job to be safe
            # This prevents bypassing concurrency control when there are DB issues
            try:
                # Try to add to queue as fallback
                control_ref = self.firestore_client.collection("system_config").document("concurrency_control")
                control_snapshot = control_ref.get()
                if control_snapshot.exists:
                    control_data = control_snapshot.to_dict() or {}
                    queue = control_data.get("queue", [])
                    if job_id not in queue:
                        queue.append(job_id)
                        control_ref.update({
                            "queue": queue,
                            "updated_at": SERVER_TIMESTAMP
                        })
                        return False, f"Transaction failed, queued as fallback: {exc}"
            except Exception as fallback_exc:
                logger.warning(
                    "[CONCURRENCY] Failed to queue job as fallback",
                    extra={
                        "job_id": job_id,
                        "error": str(fallback_exc),
                    }
                )
            # Last resort: fail-closed (queue it) if we can't even queue
            return False, f"Transaction error, failing closed (last resort): {exc}"

    def release_job_slot(self, job_id: str) -> bool:
        """Explicitly release a job slot (e.g. when job completes or fails).
        
        This function atomically removes job_id from running_job_ids and decrements running_jobs.
        Uses a transaction to ensure atomicity.
        
        Args:
            job_id: The job ID to release
            
        Returns:
            bool: True if slot was released, False if job_id was not in running_job_ids
        """
        @firestore.transactional
        def _release_transaction(transaction):
            snapshot = self.control_ref.get(transaction=transaction)
            
            if not snapshot.exists:
                logger.warning("⚠️ Concurrency control document does not exist, cannot release slot")
                return False
            
            data = snapshot.to_dict() or {}
            running_job_ids = set(data.get("running_job_ids", []))
            
            if job_id not in running_job_ids:
                logger.debug("🔓 Job %s not in running_job_ids, nothing to release", job_id)
                return False
            
            # Remove job_id and update
            running_job_ids.discard(job_id)
            new_running_count = len(running_job_ids)
            
            transaction.update(self.control_ref, {
                "running_jobs": new_running_count,
                "running_job_ids": list(running_job_ids),
                "updated_at": SERVER_TIMESTAMP,
            })
            
            logger.info(
                "🔓 Released job slot for job_id=%s (remaining running=%d)",
                job_id,
                new_running_count,
            )
            return True
        
        transaction = self.firestore_client.transaction()
        try:
            return _release_transaction(transaction)
        except Exception as exc:
            logger.exception("❌ Failed to release job slot for job_id=%s: %s", job_id, exc)
            return False

    def try_trigger_next_job(self, completed_job_id: str) -> Optional[str]:
        """Release current job slot and trigger the next job in queue (FIFO).
        
        This function atomically:
        1. Removes completed_job_id from running_job_ids
        2. Checks if queue has any jobs
        3. If yes, pops the first job (FIFO) and adds it to running_job_ids
        4. Returns the next job_id to trigger (or None if queue is empty)
        
        The caller is responsible for actually triggering the Cloud Run Job.
        
        Args:
            completed_job_id: The job ID that just completed
            
        Returns:
            Optional[str]: The next job_id to trigger, or None if queue is empty
        """
        max_concurrent = settings.max_concurrent_jobs
        
        logger.info(
            "[CONCURRENCY] Starting try_trigger_next_job",
            extra={
                "completed_job_id": completed_job_id,
                "max_concurrent": max_concurrent,
            }
        )
        print(f"[CONCURRENCY] 🔄 Starting try_trigger_next_job: completed_job_id={completed_job_id}", flush=True)
        
        @firestore.transactional
        def _try_trigger_transaction(transaction):
            snapshot = self.control_ref.get(transaction=transaction)
            
            if not snapshot.exists:
                logger.warning(
                    "[CONCURRENCY] Concurrency control document does not exist",
                    extra={"completed_job_id": completed_job_id}
                )
                print(f"[CONCURRENCY] ⚠️ Concurrency control document does not exist: completed_job_id={completed_job_id}", flush=True)
                return None
            
            data = snapshot.to_dict() or {}
            running_job_ids = set(data.get("running_job_ids", []))
            queue = data.get("queue", [])
            
            logger.info(
                "[CONCURRENCY] Current state before release",
                extra={
                    "completed_job_id": completed_job_id,
                    "running_count": len(running_job_ids),
                    "queue_size": len(queue),
                    "running_job_ids": list(running_job_ids),
                    "queue": queue,
                }
            )
            print(f"[CONCURRENCY] 📊 Before release: running={len(running_job_ids)}, queue_size={len(queue)}, running_job_ids={list(running_job_ids)}, queue={queue}", flush=True)
            
            # Remove completed job (if present)
            # Note: In sharding mode, multiple tasks may call this simultaneously.
            # The first task will remove the job_id, subsequent calls will find it already removed.
            job_was_removed = False
            if completed_job_id in running_job_ids:
                running_job_ids.discard(completed_job_id)
                job_was_removed = True
                logger.info(
                    "[CONCURRENCY] Removed completed job from running_job_ids",
                    extra={
                        "completed_job_id": completed_job_id,
                        "remaining_running": len(running_job_ids),
                    }
                )
                print(f"[CONCURRENCY] 🔓 Removed completed job: {completed_job_id}, remaining={len(running_job_ids)}", flush=True)
            else:
                # Job already removed (likely by another task in sharding mode)
                logger.info(
                    "[CONCURRENCY] Completed job not in running_job_ids (already removed)",
                    extra={
                        "completed_job_id": completed_job_id,
                        "remaining_running": len(running_job_ids),
                    }
                )
                print(f"[CONCURRENCY] ℹ️ Completed job not in running_job_ids (already removed): {completed_job_id}, remaining={len(running_job_ids)}", flush=True)
            
            # Check if we can start the next job
            # IMPORTANT: Even if completed_job_id was not in running_job_ids (already removed),
            # we should still check if we can trigger the next job from queue.
            # This handles the case where multiple tasks complete simultaneously in sharding mode.
            if len(running_job_ids) < max_concurrent and queue:
                # Pop first job from queue (FIFO)
                next_job_id = queue.pop(0)
                running_job_ids.add(next_job_id)
                
                # Update control document atomically
                transaction.update(self.control_ref, {
                    "running_jobs": len(running_job_ids),
                    "running_job_ids": list(running_job_ids),
                    "queue": queue,
                    "updated_at": SERVER_TIMESTAMP,
                })
                
                logger.info(
                    "[CONCURRENCY] Next job popped from queue",
                    extra={
                        "completed_job_id": completed_job_id,
                        "next_job_id": next_job_id,
                        "running_count": len(running_job_ids),
                        "max_concurrent": max_concurrent,
                        "queue_size": len(queue),
                    }
                )
                print(f"[CONCURRENCY] 🚀 Next job popped from queue: completed={completed_job_id}, next={next_job_id}, running={len(running_job_ids)}/{max_concurrent}, queue_size={len(queue)}", flush=True)
                return next_job_id
            else:
                # No job to trigger (queue empty or already at max)
                transaction.update(self.control_ref, {
                    "running_jobs": len(running_job_ids),
                    "running_job_ids": list(running_job_ids),
                    "queue": queue,
                    "updated_at": SERVER_TIMESTAMP,
                })
                
                if queue:
                    logger.info(
                        "[CONCURRENCY] Queue not empty but at max capacity",
                        extra={
                            "completed_job_id": completed_job_id,
                            "running_count": len(running_job_ids),
                            "max_concurrent": max_concurrent,
                            "queue_size": len(queue),
                        }
                    )
                    print(f"[CONCURRENCY] ⏳ Queue not empty but at max: running={len(running_job_ids)}/{max_concurrent}, queue_size={len(queue)}", flush=True)
                else:
                    logger.info(
                        "[CONCURRENCY] No jobs in queue, slot released",
                        extra={
                            "completed_job_id": completed_job_id,
                            "running_count": len(running_job_ids),
                        }
                    )
                    print(f"[CONCURRENCY] ✅ No jobs in queue, slot released: completed_job_id={completed_job_id}", flush=True)
                
                return None
        
        transaction = self.firestore_client.transaction()
        try:
            result = _try_trigger_transaction(transaction)
            logger.info(
                "[CONCURRENCY] try_trigger_next_job completed",
                extra={
                    "completed_job_id": completed_job_id,
                    "next_job_id": result,
                }
            )
            print(f"[CONCURRENCY] ✅ try_trigger_next_job completed: completed={completed_job_id}, next={result}", flush=True)
            return result
        except Exception as exc:
            logger.exception(
                "[CONCURRENCY] Failed to trigger next job",
                extra={
                    "completed_job_id": completed_job_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            print(f"[CONCURRENCY] ❌ Failed to trigger next job: completed={completed_job_id}, error={exc}", flush=True)
            return None

    def _trigger_cloud_run_job(self, job_id: str, drama_name: str) -> str:
        """Trigger Cloud Run Job for processing.
        
        This is a helper method that replicates the logic from relay.py
        to trigger a Cloud Run Job. It discovers file pairs, calculates
        task_count, and triggers the job.
        
        Args:
            job_id: The job ID to trigger
            drama_name: The drama name
            
        Returns:
            str: Operation name or error message
        """
        job_name = settings.process_job_name.strip()
        if not job_name:
            raise RuntimeError("PROCESSOR_JOB_NAME 未配置，无法触发 Cloud Run Job")

        # Discover file pairs to calculate total_files
        try:
            pairs = discover_file_pairs(
                drama_name=drama_name,
                source_bucket=settings.pipeline_gcs_source_bucket,
            )
            total_files = len(pairs)
            logger.info(
                "📊 Discovered %d file pairs for drama=%s (job_id=%s)",
                total_files,
                drama_name,
                job_id,
            )
        except Exception as exc:
            logger.warning(
                "⚠️ Failed to discover file pairs for drama=%s: %s. Worker will set total_files.",
                drama_name,
                exc,
            )
            total_files = None

        # Calculate task_count
        task_count = None
        if total_files is not None and total_files > 0:
            import math
            if total_files <= 100:
                task_count = total_files
            else:
                task_count = min(math.ceil(total_files / 3), 100)
            logger.info(
                "📊 Calculated task_count=%d for total_files=%d (job_id=%s)",
                task_count,
                total_files,
                job_id,
            )

        # Update Firestore job document
        jobs_collection = self.firestore_client.collection(FIRESTORE_COLLECTION)
        job_ref = jobs_collection.document(job_id)
        
        update_data = {
            "updated_at": SERVER_TIMESTAMP,
        }
        
        if total_files is not None:
            update_data["total_files"] = total_files
        
        job_snapshot = job_ref.get()
        if job_snapshot.exists:
            job_data = job_snapshot.to_dict() or {}
            if "processed_files" not in job_data:
                update_data["processed_files"] = 0
            if "failed_files" not in job_data:
                update_data["failed_files"] = 0
        else:
            logger.warning("⚠️ Job document %s does not exist", job_id)
            update_data["processed_files"] = 0
            update_data["failed_files"] = 0
        
        job_ref.update(update_data)

        # Prepare environment variables
        env_vars = [
            run_v2.EnvVar(name="JOB_ID", value=job_id),
            run_v2.EnvVar(name="DRAMA_NAME", value=drama_name),
        ]
        if settings.pipeline_default_token_ref:
            env_vars.append(
                run_v2.EnvVar(name="PIPELINE_DEFAULT_TOKEN_REF", value=settings.pipeline_default_token_ref)
            )

        # Build overrides
        overrides_kwargs = {
            "container_overrides": [
                run_v2.RunJobRequest.Overrides.ContainerOverride(env=env_vars),
            ]
        }
        
        if task_count is not None:
            overrides_kwargs["task_count"] = task_count
        
        overrides = run_v2.RunJobRequest.Overrides(**overrides_kwargs)
        
        request = run_v2.RunJobRequest(
            name=job_name,
            overrides=overrides,
        )

        # Trigger Cloud Run Job
        jobs_client = run_v2.JobsClient()
        try:
            logger.info(
                "[CONCURRENCY] Calling Cloud Run Jobs API",
                extra={
                    "job_id": job_id,
                    "drama_name": drama_name,
                    "job_name": job_name,
                    "task_count": task_count,
                    "total_files": total_files,
                }
            )
            print(f"[CONCURRENCY] 📞 Calling Cloud Run Jobs API: job_id={job_id}, job_name={job_name}, task_count={task_count}", flush=True)
            
            operation = jobs_client.run_job(request=request)
            op_name = getattr(getattr(operation, "operation", None), "name", None)
            
            logger.info(
                "[CONCURRENCY] Cloud Run Job triggered successfully",
                extra={
                    "job_id": job_id,
                    "drama_name": drama_name,
                    "job_name": job_name,
                    "operation": op_name,
                    "task_count": task_count,
                    "total_files": total_files,
                }
            )
            print(f"[CONCURRENCY] ✅ Cloud Run Job triggered: job_id={job_id}, operation={op_name}, task_count={task_count}", flush=True)
            return op_name or "unknown-operation"
        except Exception as exc:
            logger.exception(
                "[CONCURRENCY] Failed to trigger Cloud Run Job",
                extra={
                    "job_id": job_id,
                    "drama_name": drama_name,
                    "job_name": job_name,
                    "task_count": task_count,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            print(f"[CONCURRENCY] ❌ Failed to trigger Cloud Run Job: job_id={job_id}, error={exc}", flush=True)
            raise RuntimeError(f"Cloud Run Jobs API 调用失败：{exc}") from exc

    def release_and_trigger_next(self, completed_job_id: str) -> bool:
        """Release current job slot and trigger the next job in queue.
        
        This is the main method to call when a job completes. It:
        1. Releases the slot for completed_job_id
        2. Triggers the next job in queue (FIFO)
        
        Args:
            completed_job_id: The job ID that just completed
            
        Returns:
            bool: True if next job was triggered, False otherwise
        """
        logger.info(
            "[CONCURRENCY] Starting release_and_trigger_next",
            extra={
                "completed_job_id": completed_job_id,
            }
        )
        print(f"[CONCURRENCY] 🔄 Starting release_and_trigger_next: completed_job_id={completed_job_id}", flush=True)
        
        # Get next job from queue (atomically)
        next_job_id = self.try_trigger_next_job(completed_job_id)
        
        if not next_job_id:
            logger.info(
                "[CONCURRENCY] No next job to trigger",
                extra={
                    "completed_job_id": completed_job_id,
                }
            )
            print(f"[CONCURRENCY] ✅ No next job to trigger: completed_job_id={completed_job_id}", flush=True)
            return False
        
        logger.info(
            "[CONCURRENCY] Next job found, retrieving job document",
            extra={
                "completed_job_id": completed_job_id,
                "next_job_id": next_job_id,
            }
        )
        print(f"[CONCURRENCY] 📋 Next job found: completed={completed_job_id}, next={next_job_id}", flush=True)
        
        # Get job document to retrieve drama_name
        jobs_collection = self.firestore_client.collection(FIRESTORE_COLLECTION)
        job_snapshot = jobs_collection.document(next_job_id).get()
        
        if not job_snapshot.exists:
            logger.error(
                "[CONCURRENCY] Next job document does not exist",
                extra={
                    "completed_job_id": completed_job_id,
                    "next_job_id": next_job_id,
                }
            )
            print(f"[CONCURRENCY] ❌ Next job document does not exist: next_job_id={next_job_id}", flush=True)
            # Remove from running_job_ids since we can't trigger it
            self.release_job_slot(next_job_id)
            # Try to trigger the next one
            return self.release_and_trigger_next(completed_job_id)
        
        job_data = job_snapshot.to_dict() or {}
        drama_name = job_data.get("drama_name")
        
        if not drama_name:
            logger.error(
                "[CONCURRENCY] Next job missing drama_name",
                extra={
                    "completed_job_id": completed_job_id,
                    "next_job_id": next_job_id,
                }
            )
            print(f"[CONCURRENCY] ❌ Next job missing drama_name: next_job_id={next_job_id}", flush=True)
            # Remove from running_job_ids since we can't trigger it
            self.release_job_slot(next_job_id)
            # Try to trigger the next one
            return self.release_and_trigger_next(completed_job_id)
        
        logger.info(
            "[CONCURRENCY] Triggering Cloud Run Job for next job",
            extra={
                "completed_job_id": completed_job_id,
                "next_job_id": next_job_id,
                "drama_name": drama_name,
                "env": settings.app_env,
            }
        )
        print(f"[CONCURRENCY] 🚀 Triggering Cloud Run Job: completed={completed_job_id}, next={next_job_id}, drama={drama_name}, env={settings.app_env}", flush=True)
        
        # Trigger Cloud Run Job
        try:
            if settings.app_env == "development":
                # In development, we can't easily trigger a subprocess from here
                # The caller should handle this, or we skip it
                logger.info(
                    "[CONCURRENCY] Development mode: Skipping Cloud Run Job trigger",
                    extra={
                        "completed_job_id": completed_job_id,
                        "next_job_id": next_job_id,
                        "drama_name": drama_name,
                    }
                )
                print(f"[CONCURRENCY] ⚠️ Development mode: Skipping Cloud Run Job trigger: next_job_id={next_job_id}", flush=True)
                return True
            else:
                operation = self._trigger_cloud_run_job(next_job_id, drama_name)
                logger.info(
                    "[CONCURRENCY] Cloud Run Job triggered successfully for next job",
                    extra={
                        "completed_job_id": completed_job_id,
                        "next_job_id": next_job_id,
                        "drama_name": drama_name,
                        "operation": operation,
                    }
                )
                print(f"[CONCURRENCY] ✅ Cloud Run Job triggered: completed={completed_job_id}, next={next_job_id}, operation={operation}", flush=True)
                return True
        except Exception as exc:
            logger.exception(
                "[CONCURRENCY] Failed to trigger next job",
                extra={
                    "completed_job_id": completed_job_id,
                    "next_job_id": next_job_id,
                    "drama_name": drama_name,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            print(f"[CONCURRENCY] ❌ Failed to trigger next job: completed={completed_job_id}, next={next_job_id}, error={exc}", flush=True)
            # Release slot on error and try next
            self.release_job_slot(next_job_id)
            return self.release_and_trigger_next(completed_job_id)

