"""Fission (裂变素材生成) related endpoints."""

import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status

from app.api.deps import get_current_user, get_current_user_optional
from app.schemas.auth import AuthenticatedUser
from app.schemas.fission import (
    FissionJobRequest,
    FissionJobResponse,
    FissionJobDetail,
    FissionJobsListResponse,
    FissionJobListItem,
    StickerAsset,
    StickerListResponse,
)
from app.services.fission_service import FissionService

router = APIRouter()


# ==================== 任务管理 ====================


@router.post(
    "/jobs",
    response_model=FissionJobResponse,
    summary="创建裂变任务",
)
def create_fission_job(
    payload: FissionJobRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """创建裂变素材生成任务"""
    try:
        service = FissionService()
        job_id = service.create_fission_job(payload, current_user)
        return FissionJobResponse(job_id=job_id, status="QUEUED")
    except ValueError as e:
        # 验证错误（如源视频不存在）
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # 其他错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {str(e)}",
        )


@router.get(
    "/jobs",
    response_model=FissionJobsListResponse,
    summary="获取裂变任务列表",
)
def list_fission_jobs(
    job_status: Optional[str] = Query(None, alias="status", description="按状态筛选"),
    drama_name: Optional[str] = Query(None, description="按剧集名称筛选"),
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """获取裂变任务列表（支持分页）"""
    try:
        service = FissionService()
        jobs, total = service.list_fission_jobs(
            status=job_status,
            drama_name=drama_name,
            page=page,
            page_size=page_size,
        )
        return FissionJobsListResponse(jobs=jobs, total=total)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取任务列表失败: {str(e)}",
        )


@router.get(
    "/jobs/{job_id}",
    response_model=FissionJobDetail,
    summary="获取裂变任务详情",
)
def get_fission_job(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """获取裂变任务详情"""
    service = FissionService()
    job = service.get_fission_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {job_id}",
        )
    return job


@router.post(
    "/jobs/{job_id}/cancel",
    summary="取消裂变任务",
)
def cancel_fission_job(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """取消裂变任务"""
    service = FissionService()
    success = service.cancel_fission_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法取消任务（可能已完成或不存在）",
        )
    return {"message": "任务已取消", "job_id": job_id}


@router.get(
    "/jobs/{job_id}/download-url",
    summary="获取变体下载链接",
)
def get_download_url(
    job_id: str,
    variant_id: str = Query(..., description="变体ID，例如 variant_0"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """生成变体的签名下载链接（有效期1小时）"""
    service = FissionService()
    download_url = service.generate_download_url(job_id, variant_id)
    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"变体不存在: {variant_id}",
        )
    return {"download_url": download_url, "expires_in": 3600}


# ==================== 贴纸素材 ====================


@router.get(
    "/stickers",
    response_model=StickerListResponse,
    summary="获取贴纸素材列表",
)
def list_stickers(
    category: Optional[str] = Query(None, description="按分类筛选"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """获取贴纸素材列表"""
    service = FissionService()
    stickers = service.list_stickers(category=category)
    return StickerListResponse(stickers=stickers)


# ==================== 视频上传 ====================

# 本地上传目录
LOCAL_UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads" / "fission"


@router.get(
    "/videos",
    summary="获取GCS视频列表",
)
def list_videos(
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional),
):
    """列出用户的视频（优先从元数据读取）"""
    from google.cloud import storage
    from app.core.config import settings
    from app.services.video_metadata_service import VideoMetadataService

    try:
        storage_client = storage.Client()
        bucket_name = settings.fission_upload_bucket or "vigloo-fission-uploads"
        bucket = storage_client.bucket(bucket_name)

        # 如果用户已登录，优先从 Firestore 读取元数据
        if current_user:
            metadata_service = VideoMetadataService()
            metadata_videos = metadata_service.list_user_videos(current_user.user_id)

            # 转换为响应格式
            videos = []
            for meta in metadata_videos:
                videos.append({
                    "video_id": meta["video_id"],
                    "name": meta["gcs_blob_name"].split("/")[-1],  # UUID 文件名（兼容）
                    "display_name": meta.get("display_name"),
                    "original_filename": meta.get("original_filename"),
                    "gcs_path": meta["gcs_path"],
                    "size": meta["file_size"],
                    "updated": meta.get("updated_at").isoformat() if meta.get("updated_at") else None,
                })

            # 如果有元数据，直接返回
            if videos:
                return {"videos": videos}

        # 兼容模式：从 GCS 直接读取（用于旧数据或未登录用户）
        videos = []
        for blob in bucket.list_blobs():
            if blob.name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                videos.append({
                    "video_id": blob.name,  # 使用 blob name 作为临时 ID
                    "name": blob.name.split('/')[-1],
                    "display_name": None,  # 旧数据没有显示名称
                    "original_filename": None,
                    "gcs_path": f"gs://{bucket_name}/{blob.name}",
                    "size": blob.size,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                })

        return {"videos": videos}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取视频列表失败: {str(e)}",
        )


@router.get(
    "/test-gcs",
    summary="测试GCS连接（无需认证）",
)
def test_gcs_connection():
    """测试GCS连接是否正常（开发用）"""
    from google.cloud import storage
    from app.core.config import settings
    import os

    try:
        # 检查环境变量
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

        storage_client = storage.Client()
        bucket_name = settings.fission_upload_bucket or "vigloo-fission-uploads"
        bucket = storage_client.bucket(bucket_name)

        # 列出前5个视频
        videos = []
        for blob in list(bucket.list_blobs(max_results=5)):
            if blob.name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                videos.append({
                    "name": blob.name.split('/')[-1],
                    "gcs_path": f"gs://{bucket_name}/{blob.name}",
                })

        return {
            "status": "success",
            "credentials_path": creds_path,
            "bucket_name": bucket_name,
            "video_count": len(videos),
            "sample_videos": videos
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "credentials_path": os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        }


@router.post(
    "/upload",
    summary="上传视频文件到GCS",
)
async def upload_video(
    file: UploadFile = File(...),
    display_name: Optional[str] = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """上传视频文件到 GCS 并创建元数据"""
    from google.cloud import storage
    from app.core.config import settings
    from app.services.video_metadata_service import VideoMetadataService
    from app.schemas.fission import VideoUploadResponse

    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="只支持视频文件")

    try:
        # 生成唯一文件名
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "mp4"
        unique_filename = f"{uuid.uuid4()}.{file_ext}"

        # GCS路径
        bucket_name = settings.fission_upload_bucket or "vigloo-fission-uploads"
        blob_name = f"{current_user.user_id}/{unique_filename}"
        gcs_path = f"gs://{bucket_name}/{blob_name}"

        # 读取文件内容
        content = await file.read()

        # 上传到GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # 设置内容类型
        content_type = file.content_type or "video/mp4"
        blob.upload_from_string(content, content_type=content_type)

        # 确定显示名称
        if not display_name or not display_name.strip():
            # 使用原始文件名（去扩展名）
            display_name = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename

        # 创建元数据
        metadata_service = VideoMetadataService()
        try:
            video_id = metadata_service.create_video_metadata(
                user_id=current_user.user_id,
                gcs_path=gcs_path,
                gcs_bucket=bucket_name,
                gcs_blob_name=blob_name,
                display_name=display_name.strip(),
                original_filename=file.filename,
                file_size=len(content),
                content_type=content_type,
                file_extension=file_ext,
            )
        except Exception as e:
            # 元数据创建失败，删除已上传的文件
            blob.delete()
            raise HTTPException(status_code=500, detail=f"元数据创建失败: {str(e)}")

        return VideoUploadResponse(
            video_id=video_id,
            filename=unique_filename,
            display_name=display_name.strip(),
            original_filename=file.filename,
            gcs_path=gcs_path,
            size=len(content),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败: {str(e)}",
        )


@router.post(
    "/upload-url",
    summary="获取视频上传URL（GCS，需要网络）",
)
def get_upload_url(
    payload: dict,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """生成视频上传的签名URL"""
    from google.cloud import storage
    from app.core.config import settings
    import datetime
    import uuid

    filename = payload.get("filename", "video.mp4")
    content_type = payload.get("content_type", "video/mp4")

    # 生成唯一文件名
    file_ext = filename.split(".")[-1] if "." in filename else "mp4"
    unique_filename = f"{uuid.uuid4()}.{file_ext}"

    # GCS路径（使用专门的上传bucket）
    bucket_name = settings.fission_upload_bucket or "vigloo-fission-uploads"
    blob_name = f"{current_user.user_id}/{unique_filename}"
    gcs_path = f"gs://{bucket_name}/{blob_name}"

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # 生成签名URL（有效期15分钟）
        upload_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="PUT",
            content_type=content_type,
        )

        return {
            "upload_url": upload_url,
            "gcs_path": gcs_path,
            "expires_in": 900,  # 15分钟
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成上传URL失败: {str(e)}",
        )


@router.patch(
    "/videos/{video_id}",
    summary="重命名视频",
)
def rename_video(
    video_id: str,
    payload: dict,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """更新视频显示名称"""
    from app.services.video_metadata_service import VideoMetadataService
    from app.schemas.fission import VideoRenameRequest

    # 验证请求数据
    try:
        rename_request = VideoRenameRequest(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"请求数据无效: {str(e)}")

    metadata_service = VideoMetadataService()

    try:
        success = metadata_service.update_display_name(
            video_id=video_id,
            user_id=current_user.user_id,
            display_name=rename_request.display_name,
        )

        if not success:
            raise HTTPException(status_code=404, detail="视频不存在")

        return {
            "video_id": video_id,
            "display_name": rename_request.display_name,
            "message": "重命名成功",
        }

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")
