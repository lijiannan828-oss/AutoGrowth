"\"\"\"Pipeline (GDrive/GCS) related endpoints.\"\"\""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.cloud import firestore, storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.firestore import get_firestore_client
from app.schemas.auth import AuthenticatedUser
from app.schemas.pipeline import (
    DownloadLinkResponse,
    DramaJobRow,
    FailureDetail,
    FolderBrowseNode,
    GDriveProgramStatus,
    ManualProcessRequest,
    ManualProcessResponse,
    NasDownloadRequest,
    NasDownloadResponse,
    PipelineFolder,
    PipelineJobsResponse,
    PipelineJobsStatsResponse,
    PipelineRoot,
    ProcessStatus,
    TransferJobRequest,
    TransferJobResponse,
    TransferStatus,
    ZipDownloadRequest,
    ZipDownloadResponse,
    ZipTaskStatusResponse,
    RetryProcessResponse,
)
from app.services.pipeline_status_service import get_pipeline_status_service
from app.services.pipeline_transfer_service import PipelineTransferService
from app.services.pipeline_process_service import PipelineProcessService
from app.services.pipeline_zip_service import PipelineZipService

router = APIRouter()


@router.get(
    "/gdrive-status",
    response_model=list[GDriveProgramStatus],
    summary="列出 GDrive 剧集状态（含 GCS 匹配情况）",
)
def get_gdrive_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    service = get_pipeline_status_service(current_user)
    return service.list_program_status()


@router.get(
    "/gdrive-folders",
    response_model=list[PipelineFolder],
    summary="列出剧集下的子目录（含同步状态）",
)
def get_gdrive_folders(
    gdrive_path: str = Query(..., description="剧集在 GDrive 的路径"),
    include_children: bool = Query(
        False, description="是否包含多级子目录（默认仅返回直系子文件夹）"
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    service = get_pipeline_status_service(current_user)
    folders = service.list_program_folders(gdrive_path, include_children=include_children)
    if folders is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定剧集",
        )
    return folders


@router.get(
    "/gdrive-roots",
    response_model=list[PipelineRoot],
    summary="列出 pipeline 配置的根目录",
)
def get_gdrive_roots(current_user: AuthenticatedUser = Depends(get_current_user)):
    del current_user
    return [
        PipelineRoot(label=label, folder_id=folder_id)
        for label, folder_id in settings.pipeline_gdrive_roots
    ]


@router.get(
    "/unprocessed-dramas",
    response_model=list[str],
    summary="列出待压制（源桶存在但 processed 缺失）的剧集",
)
def list_unprocessed_dramas(current_user: AuthenticatedUser = Depends(get_current_user)):
    service = get_pipeline_status_service(current_user)
    return service.list_unprocessed_dramas()


@router.get(
    "/gdrive-browse",
    response_model=list[FolderBrowseNode],
    summary="按需列出指定 GDrive 目录的直接子目录",
)
def browse_gdrive_folder(
    drive_folder_id: str = Query(..., description="目标 GDrive 文件夹 ID"),
    gcs_prefix: str | None = Query(
        default=None,
        description="可选 GCS 前缀，用于比对同步状态。例如 'ProgramA/Episodes'",
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        service = get_pipeline_status_service(current_user)
        return service.browse_drive_folder(drive_folder_id, gcs_prefix)
    except Exception as exc:
        import traceback
        error_detail = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
        print(f"❌ [gdrive-browse] Error: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"浏览 GDrive 目录失败: {str(exc)}",
        ) from exc


@router.post(
    "/transfer",
    response_model=TransferJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建并触发 GDrive -> GCS 传输任务",
)
def create_transfer_job(
    payload: TransferJobRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    service = PipelineTransferService()
    try:
        return service.enqueue_transfer_job(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/retry-process/{failure_id}",
    response_model=RetryProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="触发压制失败的单文件重试",
)
def retry_process_failure(
    failure_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    service = PipelineProcessService()
    try:
        job_id = service.enqueue_retry_job(failure_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return RetryProcessResponse(job_id=job_id, status="QUEUED")


@router.post(
    "/process-manual",
    response_model=ManualProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动触发压制任务（无需重新传输）",
)
def trigger_manual_process(
    payload: ManualProcessRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    service = PipelineProcessService()
    try:
        job_id = service.trigger_manual_process_job(
            payload.drama_name, payload.file_paths, current_user
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return ManualProcessResponse(job_id=job_id, status="QUEUED")


def _translate_error(error_message: str | None) -> str:
    """将原始错误信息解译为用户友好的错误原因"""
    if not error_message:
        return "未知错误"
    
    # 错误解译映射
    error_map = {
        "FileNotFoundError": "文件未找到",
        "PermissionError": "权限不足",
        "TimeoutError": "操作超时",
        "ConnectionError": "连接失败",
        "StorageError": "存储错误",
        "ProcessingError": "处理失败",
        "InvalidFormat": "格式无效",
    }
    
    # 尝试匹配常见错误
    for key, value in error_map.items():
        if key in error_message:
            return value
    
    # 如果错误信息太长，截取前100个字符
    if len(error_message) > 100:
        return error_message[:100] + "..."
    
    return error_message


def _get_transfer_state(job_data: Dict) -> str:
    """获取传输状态"""
    job_status = job_data.get("status", "").upper()
    stage = job_data.get("stage")
    if stage in (None, 0, 1):
        return job_status
    return (job_data.get("transfer_status") or job_status).upper()


def _get_process_state(job_data: Dict) -> str:
    """获取压制状态"""
    job_status = job_data.get("status", "").upper()
    stage = job_data.get("stage")
    if stage and stage >= 2:
        return job_status
    return (job_data.get("process_status") or "").upper()


def _has_transfer_failure(job_data: Dict, failures: List[FailureDetail]) -> bool:
    """检查是否有传输失败"""
    return any(f.stage == "transfer" for f in failures) or _get_transfer_state(job_data) == "FAILED"


def _has_process_failure(job_data: Dict, failures: List[FailureDetail]) -> bool:
    """检查是否有压制失败"""
    return any(f.stage == "process" for f in failures) or _get_process_state(job_data) in ("FAILED", "FAILED_STAGE2")


def _is_in_progress(job_data: Dict, failures: List[FailureDetail]) -> bool:
    """判断任务是否进行中"""
    transfer_state = _get_transfer_state(job_data)
    process_state = _get_process_state(job_data)
    is_complete = process_state == "COMPLETE"
    is_failed = transfer_state == "FAILED" or process_state in ("FAILED", "FAILED_STAGE2") or _has_transfer_failure(job_data, failures) or _has_process_failure(job_data, failures)
    return not is_complete and not is_failed


def _is_transferring(job_data: Dict, failures: List[FailureDetail]) -> bool:
    """判断任务是否传输中"""
    state = _get_transfer_state(job_data)
    if _has_transfer_failure(job_data, failures):
        return False
    return state in ("TRANSFERRING", "QUEUED")


def _is_processing(job_data: Dict, failures: List[FailureDetail]) -> bool:
    """判断任务是否压制中"""
    state = _get_process_state(job_data)
    if _has_process_failure(job_data, failures):
        return False
    # 已传输完成在压制中：stage=2 且 status=PROCESSING
    # 单独在压制：type=manual 且 stage=1 且 status=PROCESSING
    if state == "PROCESSING":
        return True
    # 检查是否是 manual 类型且 stage=1 的压制任务
    job_type = job_data.get("type", "").lower()
    if job_type == "manual" and state == "PROCESSING":
        return True
    return False


def _is_failed(job_data: Dict, failures: List[FailureDetail]) -> bool:
    """判断任务是否失败"""
    transfer_state = _get_transfer_state(job_data)
    process_state = _get_process_state(job_data)
    return (
        transfer_state == "FAILED"
        or process_state in ("FAILED", "FAILED_STAGE2")
        or _has_transfer_failure(job_data, failures)
        or _has_process_failure(job_data, failures)
    )


def _is_completed_in_last_30_days(job_data: Dict) -> bool:
    """判断任务是否在最近30天内完成"""
    process_state = _get_process_state(job_data)
    if process_state != "COMPLETE":
        return False
    updated_at = job_data.get("updated_at")
    if not updated_at:
        return False
    if isinstance(updated_at, datetime):
        last_updated = updated_at
    else:
        try:
            last_updated = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return False
    now = datetime.utcnow()
    if last_updated.tzinfo:
        now = now.replace(tzinfo=last_updated.tzinfo)
    diff_days = (now - last_updated).total_seconds() / (24 * 60 * 60)
    return diff_days <= 30


@router.get(
    "/jobs/stats",
    response_model=PipelineJobsStatsResponse,
    summary="获取任务状态统计",
)
def get_pipeline_jobs_stats(current_user: AuthenticatedUser = Depends(get_current_user)):
    """获取各状态的任务数量统计"""
    del current_user
    
    client = get_firestore_client()
    jobs_ref = client.collection("pipeline_jobs")
    # 查询所有任务（不限制数量，用于统计）
    query = jobs_ref.order_by("updated_at", direction=firestore.Query.DESCENDING)
    job_snapshots = list(query.stream())
    
    # 获取失败信息
    failure_map: Dict[str, List[FailureDetail]] = {}
    if job_snapshots:
        failure_collection = client.collection("processing_failures")
        job_ids = [snap.id for snap in job_snapshots]
        for job_id in job_ids:
            failure_query = failure_collection.where("job_id", "==", job_id)
            failure_docs = list(failure_query.stream())
            if not failure_docs:
                continue
            failure_map[job_id] = [
                FailureDetail(
                    stage="process",
                    file_path=doc.to_dict().get("video_gcs_path"),
                    error_message=_translate_error(doc.to_dict().get("error_message", "")),
                )
                for doc in failure_docs
            ]
    
    # 统计各状态数量
    in_progress_count = 0
    transferring_count = 0
    processing_count = 0
    failed_count = 0
    completed_count = 0
    
    for snap in job_snapshots:
        data = snap.to_dict() or {}
        failures = failure_map.get(snap.id, [])
        
        if _is_in_progress(data, failures):
            in_progress_count += 1
        if _is_transferring(data, failures):
            transferring_count += 1
        if _is_processing(data, failures):
            processing_count += 1
        if _is_failed(data, failures):
            failed_count += 1
        if _is_completed_in_last_30_days(data):
            completed_count += 1
    
    return PipelineJobsStatsResponse(
        in_progress_count=in_progress_count,
        transferring_count=transferring_count,
        processing_count=processing_count,
        failed_count=failed_count,
        completed_count=completed_count,
    )


@router.get(
    "/jobs",
    response_model=PipelineJobsResponse,
    summary="列出最近的传输/压制任务（任务看板）",
)
def list_pipeline_jobs(current_user: AuthenticatedUser = Depends(get_current_user)):
    del current_user  # 权限由依赖完成，此处无需额外字段

    client = get_firestore_client()
    jobs_ref = client.collection("pipeline_jobs")
    # NOTE: 默认的单字段索引即可支持按 updated_at 排序，如需复合过滤需在控制台创建索引
    query = (
        jobs_ref.order_by("updated_at", direction=firestore.Query.DESCENDING)
        .limit(50)
    )

    job_snapshots = list(query.stream())
    failure_map: Dict[str, List[FailureDetail]] = {}

    if job_snapshots:
        failure_collection = client.collection("processing_failures")
        job_ids = [snap.id for snap in job_snapshots]
        # Firestore 需单独查询；这里逐个 job_id 查询，便于避免复合索引
        for job_id in job_ids:
            failure_query = failure_collection.where("job_id", "==", job_id)
            failure_docs = list(failure_query.stream())
            if not failure_docs:
                continue
            failure_map[job_id] = [
                FailureDetail(
                    stage="process",
                    file_path=doc.to_dict().get("video_gcs_path"),
                    error_message=_translate_error(doc.to_dict().get("error_message", "")),
                )
                for doc in failure_docs
            ]

    items: List[DramaJobRow] = []
    for snap in job_snapshots:
        data = snap.to_dict() or {}
        drama_name = data.get("drama_name") or data.get("gdrive_path") or "Unknown"
        job_status = data.get("status")
        stage = data.get("stage")
        progress_text = data.get("progress")
        job_type = data.get("type")
        processed_files = data.get("processed_files")
        processed_total = data.get("processed_total")
        language_details = data.get("language_details")

        transfer_status = TransferStatus(
            status=job_status if stage in (None, 0, 1) else data.get("transfer_status") or job_status,
            progress_text=progress_text if stage in (None, 0, 1) else data.get("transfer_progress"),
        )

        process_status = ProcessStatus(
            status=job_status if stage and stage >= 2 else data.get("process_status"),
            progress_text=progress_text if stage and stage >= 2 else data.get("process_progress"),
            processed_count=processed_files,
            total_count=processed_total,
            language_details=language_details,
        )

        failures: List[FailureDetail] = []
        if data.get("status") == "FAILED" and (stage is None or stage <= 1):
            failures.append(
                FailureDetail(
                    stage="transfer",
                    file_path=data.get("gdrive_path"),
                    error_message=_translate_error(progress_text or "传输失败"),
                )
            )

        # 添加处理失败，并应用错误解译
        process_failures = failure_map.get(snap.id, [])
        failures.extend(process_failures)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, datetime):
            last_updated = updated_at
        else:
            last_updated = None

        items.append(
            DramaJobRow(
                drama_name=drama_name,
                job_id=snap.id,
                job_type=job_type,
                source_path=data.get("gdrive_path"),
                transfer=transfer_status,
                process=process_status,
                failures=failures,
                last_updated=last_updated,
            )
        )

    return PipelineJobsResponse(items=items)


def _parse_gs_path(path: str) -> Tuple[str, str]:
    if not path or not path.startswith("gs://"):
        raise ValueError("file_path 必须为 gs://bucket/object 形式")
    remainder = path[5:]
    if "/" not in remainder:
        raise ValueError("file_path 缺少对象路径")
    bucket, object_name = remainder.split("/", 1)
    if not bucket or not object_name:
        raise ValueError("file_path 缺少 bucket 或 object")
    return bucket, object_name


def _get_storage_client_with_signing():
    """Get a Storage Client configured with service account credentials for signing URLs.
    
    This is required because generate_signed_url needs a private key to sign URLs.
    In Cloud Run, default credentials (Compute Engine credentials) only have a token,
    not a private key, so we need to use a service account key file.
    
    In Cloud Run, secrets are mounted to /secrets/{secret-name} when using --set-secrets.
    The GOOGLE_APPLICATION_CREDENTIALS environment variable contains the secret name,
    not the file path. We need to construct the actual mount path.
    """
    import os
    from google.oauth2 import service_account
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Try multiple possible paths for the service account key file
    possible_paths = []
    
    # 1. Check if GOOGLE_APPLICATION_CREDENTIALS points to a file path
    creds_env = settings.google_application_credentials
    if creds_env:
        possible_paths.append(creds_env)
        # 2. If it's a secret name (not a path), try Cloud Run secret mount path
        # Cloud Run mounts secrets to /secrets/{secret-name}
        if not os.path.exists(creds_env) and not os.path.sep in creds_env:
            # Looks like a secret name, try the mount path
            possible_paths.append(f"/secrets/{creds_env}")
    
    # 3. Common Cloud Run secret mount paths
    # Priority: sa-run-prod-key (runtime service account) > gcp-sa-key (deployment service account)
    common_secret_names = ["sa-run-prod-key", "SA_RUN_PROD_KEY", "gcp-sa-key", "GOOGLE_APPLICATION_CREDENTIALS"]
    for secret_name in common_secret_names:
        possible_paths.append(f"/secrets/{secret_name}")
    
    # Try each possible path
    for creds_path in possible_paths:
        if creds_path and os.path.exists(creds_path):
            try:
                logger.info(f"[Storage Client] Attempting to load service account from {creds_path}")
                print(f"[Storage Client] Attempting to load service account from {creds_path}")
                credentials = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                logger.info(f"[Storage Client] Successfully loaded service account from {creds_path}")
                print(f"[Storage Client] Successfully loaded service account from {creds_path}")
                return storage.Client(credentials=credentials, project=credentials.project_id)
            except Exception as e:
                logger.warning(f"[Storage Client] Failed to load service account from {creds_path}: {e}")
                print(f"[Storage Client] Failed to load service account from {creds_path}: {e}")
                continue
    
    # Fallback to default credentials (may not work for signed URLs in Cloud Run)
    logger.warning("[Storage Client] No service account key file found, using default credentials (may fail for signed URLs)")
    print("[Storage Client] No service account key file found, using default credentials (may fail for signed URLs)")
    return storage.Client()


@router.get(
    "/download-link",
    response_model=DownloadLinkResponse,
    summary="生成单个文件的签名下载链接",
)
def get_download_link(
    file_path: str = Query(..., description="完整的 GCS 路径，例如 gs://bucket/path/file.mp4"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    del current_user
    try:
        bucket_name, object_name = _parse_gs_path(file_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    storage_client = _get_storage_client_with_signing()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    if not blob.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在或无权限访问")

    ttl_seconds = max(60, settings.download_signed_url_ttl_seconds)
    expires_delta = timedelta(seconds=ttl_seconds)
    try:
        url = blob.generate_signed_url(
            expiration=expires_delta,
            method="GET",
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    expires_at = datetime.utcnow() + expires_delta
    return DownloadLinkResponse(url=url, expires_at=expires_at)


@router.post(
    "/download-zip",
    response_model=ZipDownloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="触发 ZIP 打包任务",
)
def create_zip_download_task(
    payload: ZipDownloadRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    service = PipelineZipService()
    try:
        task_id = service.enqueue_zip_task(payload.paths, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return ZipDownloadResponse(task_id=task_id)


@router.get(
    "/zip-task/{task_id}",
    response_model=ZipTaskStatusResponse,
    summary="获取 ZIP 任务状态",
)
def get_zip_task_status(
    task_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """获取 ZIP 任务的当前状态"""
    del current_user
    
    client = get_firestore_client()
    task_ref = client.collection("zip_tasks").document(task_id)
    snapshot = task_ref.get()
    
    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ZIP 任务 {task_id} 不存在"
        )
    
    data = snapshot.to_dict() or {}
    return ZipTaskStatusResponse(
        task_id=task_id,
        status=data.get("status", "QUEUED"),
        status_message=data.get("status_message"),
        progress=data.get("progress"),
        download_url=data.get("download_url"),
        speed_bps=data.get("speed_bps"),
        estimated_seconds=data.get("estimated_seconds"),
        downloaded_bytes=data.get("downloaded_bytes"),
        total_bytes=data.get("total_bytes"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


@router.post(
    "/download-to-nas",
    response_model=NasDownloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建 NAS 下载任务",
)
def create_nas_download_task(
    payload: NasDownloadRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    firestore_client = get_firestore_client()
    doc_ref = firestore_client.collection("nas_download_tasks").document()
    doc_ref.set(
        {
            "files": payload.files,
            "drama_name": payload.drama_name,
            "notes": payload.notes,
            "status": "QUEUED",
            "requested_by": current_user.email,
            "requested_by_name": current_user.name,
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
        }
    )
    return NasDownloadResponse(task_id=doc_ref.id)


def _normalize_prefix(prefix: str | None) -> str:
    if not prefix:
        return ""
    trimmed = prefix.strip().lstrip("/")
    return trimmed.rstrip("/")


def _extract_name(path: str) -> str:
    normalized = path.rstrip("/")
    if not normalized:
        return ""
    return normalized.split("/")[-1]


@router.get(
    "/processed-files",
    summary="浏览已压制资源目录",
    response_model=list[dict],
)
def list_processed_files(
    prefix: str | None = Query(
        default=None,
        description="可选：指定目录前缀，例如 KR065P01S01_죽여야하는,로맨스/[Final]Episodes",
    ),
    keyword: str | None = Query(
        default=None,
        alias="q",
        description="可选：按名称包含过滤",
    ),
    scope: str | None = Query(
        default=None,
        alias="type",
        description="processed=已压制（默认）/source=待压制",
    ),
    drama: str | None = Query(
        default=None,
        description="可选：根据剧集路径自动拼接前缀",
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    del current_user
    effective_scope = (scope or "processed").lower()
    if effective_scope not in {"processed", "source"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="type 仅支持 processed 或 source",
        )

    if effective_scope == "processed":
        bucket_name = settings.pipeline_gcs_processed_bucket
    else:
        bucket_name = settings.pipeline_gcs_source_bucket
    if not bucket_name:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未配置目标 GCS 桶",
        )

    effective_input_prefix = prefix or drama
    normalized_prefix = _normalize_prefix(effective_input_prefix)
    effective_prefix = f"{normalized_prefix}/" if normalized_prefix else ""

    storage_client = storage.Client()
    iterator = storage_client.list_blobs(
        bucket_name,
        prefix=effective_prefix,
        delimiter="/",
    )

    files: List[dict] = []
    blobs = list(iterator)
    for blob in blobs:
        relative_path = (
            blob.name[len(effective_prefix) :]
            if effective_prefix and blob.name.startswith(effective_prefix)
            else blob.name
        )
        files.append(
            {
                "name": _extract_name(relative_path),
                "path": blob.name,
                "is_directory": False,
                "size": blob.size,
                "updated_at": blob.updated.isoformat() if blob.updated else None,
            }
        )

    directories: List[dict] = []
    for dir_prefix in sorted(iterator.prefixes):
        if not dir_prefix:
            continue
        relative = (
            dir_prefix[len(effective_prefix) :]
            if effective_prefix and dir_prefix.startswith(effective_prefix)
            else dir_prefix
        ).rstrip("/")
        if not relative:
            continue
        directories.append(
            {
                "name": _extract_name(relative),
                "path": dir_prefix.rstrip("/"),
                "is_directory": True,
                "size": None,
                "updated_at": None,
            }
        )

    keyword_lower = keyword.lower() if keyword else None

    def matches(entry: dict) -> bool:
        if not keyword_lower:
            return True
        return keyword_lower in entry["name"].lower()

    results = [item for item in directories if matches(item)]
    results.extend(item for item in files if matches(item))
    return results


class BatchDownloadRequest(BaseModel):
    paths: List[str] = Field(..., description="GCS 路径列表（支持文件或目录）")

class DownloadItem(BaseModel):
    path: str = Field(..., description="相对路径（用于本地保存）")
    url: str = Field(..., description="下载链接")
    size: int = Field(..., description="文件大小（字节）")

class BatchDownloadResponse(BaseModel):
    files: List[DownloadItem]
    errors: List[str] = Field(default_factory=list, description="处理过程中遇到的错误信息（用于调试）")


@router.post(
    "/batch-urls",
    response_model=BatchDownloadResponse,
    summary="批量获取下载链接",
    description="解析传入的路径（支持目录），返回所有文件的下载链接和相对路径，用于前端直接下载。",
)
def get_batch_download_urls(
    payload: BatchDownloadRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    # del current_user
    import logging
    logger = logging.getLogger(__name__)
    
    # Initialize Storage Client with service account credentials if available
    # This is required for generate_signed_url which needs a private key
    storage_client = _get_storage_client_with_signing()
    
    results: List[DownloadItem] = []
    errors: List[str] = []
    
    logger.info(f"[Batch URLs] Received {len(payload.paths)} paths: {payload.paths}")
    print(f"[Batch URLs] Received {len(payload.paths)} paths: {payload.paths}")
    
    # 预处理：找到所有选定路径的共同前缀，以便生成合理的相对路径
    # 如果只有一个路径且是目录，相对路径从该目录内部开始
    # 如果有多个路径，相对路径包含顶层目录名
    
    for user_path in payload.paths:
        try:
            logger.info(f"[Batch URLs] Processing path: {user_path}")
            print(f"[Batch URLs] Processing path: {user_path}")
            
            bucket_name, object_name = _parse_gs_path(user_path)
            logger.info(f"[Batch URLs] Parsed - bucket: {bucket_name}, object: {object_name}")
            print(f"[Batch URLs] Parsed - bucket: {bucket_name}, object: {object_name}")
            
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            
            # 1. Check if it's a single file
            logger.info(f"[Batch URLs] Checking if blob exists: {object_name}")
            print(f"[Batch URLs] Checking if blob exists: {object_name}")
            
            exists_result = blob.exists()
            logger.info(f"[Batch URLs] Blob exists result: {exists_result}")
            print(f"[Batch URLs] Blob exists result: {exists_result}")
            
            if exists_result:
                logger.info(f"[Batch URLs] Found single file: {object_name}, size: {blob.size}")
                print(f"[Batch URLs] Found single file: {object_name}, size: {blob.size}")
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(hours=24),
                    method="GET",
                )
                results.append(DownloadItem(
                    path=object_name,
                    url=url,
                    size=blob.size or 0
                ))
                logger.info(f"[Batch URLs] Added single file: {object_name}")
                print(f"[Batch URLs] Added single file: {object_name}")
                continue
            
            # 2. Treat as directory
            prefix = object_name.rstrip("/") + "/"
            logger.info(f"[Batch URLs] Treating as directory, prefix: {prefix}")
            print(f"[Batch URLs] Treating as directory, prefix: {prefix}")
            
            try:
                blobs = list(storage_client.list_blobs(bucket_name, prefix=prefix))
                logger.info(f"[Batch URLs] Found {len(blobs)} blobs with prefix {prefix}")
                print(f"[Batch URLs] Found {len(blobs)} blobs with prefix {prefix}")
                
                if len(blobs) == 0:
                    logger.warning(f"[Batch URLs] Warning: No blobs found for prefix {prefix}")
                    print(f"[Batch URLs] Warning: No blobs found for prefix {prefix}")
                    # Try without trailing slash
                    prefix_no_slash = object_name.rstrip("/")
                    logger.info(f"[Batch URLs] Trying alternative prefix: {prefix_no_slash}/")
                    print(f"[Batch URLs] Trying alternative prefix: {prefix_no_slash}/")
                    blobs_alt = list(storage_client.list_blobs(bucket_name, prefix=f"{prefix_no_slash}/"))
                    logger.info(f"[Batch URLs] Alternative search found {len(blobs_alt)} blobs")
                    print(f"[Batch URLs] Alternative search found {len(blobs_alt)} blobs")
                    if len(blobs_alt) > 0:
                        blobs = blobs_alt
                        prefix = f"{prefix_no_slash}/"
                    else:
                        # 尝试列出所有以该路径开头的对象（包括子目录）
                        logger.info(f"[Batch URLs] Trying broader search without trailing slash")
                        print(f"[Batch URLs] Trying broader search without trailing slash")
                        blobs_broad = list(storage_client.list_blobs(bucket_name, prefix=prefix_no_slash))
                        logger.info(f"[Batch URLs] Broader search found {len(blobs_broad)} blobs")
                        print(f"[Batch URLs] Broader search found {len(blobs_broad)} blobs")
                        if len(blobs_broad) > 0:
                            blobs = blobs_broad
                            prefix = prefix_no_slash
                
                for b in blobs:
                    logger.info(f"[Batch URLs] Processing blob: {b.name}, size: {b.size}")
                    print(f"[Batch URLs] Processing blob: {b.name}, size: {b.size}")
                    url = b.generate_signed_url(
                        version="v4",
                        expiration=timedelta(hours=24),
                        method="GET",
                    )
                    results.append(DownloadItem(
                        path=b.name,
                        url=url,
                        size=b.size or 0
                    ))
                
                logger.info(f"[Batch URLs] Added {len(blobs)} files from path {user_path}")
                print(f"[Batch URLs] Added {len(blobs)} files from path {user_path}")
            except Exception as list_err:
                import traceback
                list_trace = traceback.format_exc()
                error_msg = f"Error listing blobs for prefix {prefix}: {list_err}"
                logger.error(f"[Batch URLs] {error_msg}")
                logger.error(f"[Batch URLs] Traceback: {list_trace}")
                print(f"[Batch URLs] {error_msg}")
                print(f"[Batch URLs] Traceback: {list_trace}")
                errors.append(f"{user_path}: {error_msg}")
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            error_msg = f"Error resolving path {user_path}: {e}"
            logger.error(f"[Batch URLs] {error_msg}")
            logger.error(f"[Batch URLs] Traceback: {error_trace}")
            print(f"[Batch URLs] {error_msg}")
            print(f"[Batch URLs] Traceback: {error_trace}")
            errors.append(f"{user_path}: {str(e)}")
            # Continue processing other paths
            continue
    
    logger.info(f"[Batch URLs] Returning {len(results)} total files, {len(errors)} errors")
    print(f"[Batch URLs] Returning {len(results)} total files, {len(errors)} errors")
    
    if errors:
        logger.warning(f"[Batch URLs] Errors encountered: {errors}")
        print(f"[Batch URLs] Errors encountered: {errors}")
    
    return BatchDownloadResponse(files=results, errors=errors)


@router.get(
    "/download-proxy",
    summary="代理下载 GCS 文件（解决 CORS 问题）",
    description="通过后端代理下载 GCS 文件，返回流式响应，避免 CORS 限制。",
)
def download_proxy(
    file_path: str = Query(..., description="完整的 GCS 路径，例如 gs://bucket/path/file.mp4"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """代理下载 GCS 文件，解决前端 CORS 问题。"""
    from fastapi.responses import StreamingResponse
    import io
    
    try:
        bucket_name, object_name = _parse_gs_path(file_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    
    if not blob.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在或无权限访问")
    
    # 刷新 blob 元数据以确保获取最新的大小信息
    try:
        blob.reload()
        print(f"[Download Proxy] Blob 元数据已刷新: size={blob.size}")
    except Exception as e:
        print(f"[Download Proxy] Warning: 无法刷新 blob 元数据: {e}")

    def generate():
        """生成器函数，流式传输文件内容。"""
        try:
            print(f"[Download Proxy] 开始流式传输文件: {file_path}, blob.size: {blob.size}")
            bytes_sent = 0
            chunk_count = 0
            
            # 使用 blob.open("rb") 打开文件流
            file_stream = blob.open("rb")
            try:
                print(f"[Download Proxy] 文件流已打开")
                while True:
                    chunk = file_stream.read(8192)  # 8KB chunks
                    if not chunk:
                        print(f"[Download Proxy] 读取到空 chunk，结束循环")
                        break
                    bytes_sent += len(chunk)
                    chunk_count += 1
                    yield chunk
                    # 每 100 个 chunk 打印一次进度
                    if chunk_count % 100 == 0:
                        print(f"[Download Proxy] 已发送 {chunk_count} 个 chunk, {bytes_sent} 字节")
                print(f"[Download Proxy] 文件传输完成: {file_path}, 已发送: {bytes_sent} 字节, {chunk_count} 个 chunk")
            finally:
                file_stream.close()
                print(f"[Download Proxy] 文件流已关闭")
        except Exception as e:
            print(f"[Download Proxy] Error streaming file {file_path}: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # 获取文件名用于 Content-Disposition header
    filename = object_name.split("/")[-1]

    # 清理 Windows 非法字符: \ / : * ? " < > |
    import re
    safe_filename = re.sub(r'[\\/:*?"<>|]', '_', filename)

    return StreamingResponse(
        generate(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Length": str(blob.size or 0),
            "Access-Control-Allow-Origin": "*",  # 允许跨域
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*",
        },
    )


