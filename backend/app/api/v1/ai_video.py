"""AI Video generation API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.schemas.ai_video import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoTaskStatus,
    VideoListResponse,
    VideoGenerationStatus,
)
from app.services.ai_video_service import AIVideoService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
ai_video_service = AIVideoService()


@router.post("/generate", response_model=VideoGenerationResponse, tags=["AI Video"])
async def generate_video(request: VideoGenerationRequest):
    """
    生成AI视频
    
    - **prompt**: 文字指令描述（必填，10-2000字符）
    - **style**: 画风风格（realistic/anime/drama/cinematic/cartoon）
    - **duration**: 视频时长（3-60秒）
    - **aspect_ratio**: 视频比例（9:16/16:9/1:1）
    - **character_description**: 人物设定（可选）
    - **scene_description**: 场景要求（可选）
    - **camera_movement**: 镜头语言（可选）
    - **audio_style**: 音频风格（可选）
    """
    try:
        result = await ai_video_service.generate_video(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频生成失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=VideoTaskStatus, tags=["AI Video"])
async def get_task_status(task_id: str):
    """
    获取视频生成任务状态
    
    - **task_id**: 任务ID
    """
    task = await ai_video_service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/tasks", response_model=VideoListResponse, tags=["AI Video"])
async def list_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[VideoGenerationStatus] = Query(None, description="按状态筛选"),
):
    """
    获取视频生成任务列表
    
    - **page**: 页码（默认1）
    - **page_size**: 每页数量（默认20，最大100）
    - **status**: 按状态筛选（可选：pending/processing/completed/failed）
    """
    result = await ai_video_service.list_tasks(page, page_size, status)
    return VideoListResponse(**result)


@router.delete("/tasks/{task_id}", tags=["AI Video"])
async def delete_task(task_id: str):
    """
    删除视频生成任务

    - **task_id**: 任务ID
    """
    task = await ai_video_service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 从内存缓存中删除
    if task_id in ai_video_service.tasks:
        del ai_video_service.tasks[task_id]

    # 从 Firestore 删除任务文档
    try:
        from app.core.firestore import get_firestore_client
        db = get_firestore_client()
        db.collection("ai_video_jobs").document(task_id).delete()
    except Exception as e:
        logger.warning(f"Firestore 删除失败: {e}")

    # 从 GCS 删除生成的文件
    try:
        from google.cloud import storage as gcs_storage
        bucket_name = settings.fission_upload_bucket or "vigloo-fission-uploads"
        client = gcs_storage.Client()
        bucket = client.bucket(bucket_name)
        # 删除视频文件
        video_blob = bucket.blob(f"ai-video/outputs/{task_id}.mp4")
        if video_blob.exists():
            video_blob.delete()
        # 删除缩略图
        thumb_blob = bucket.blob(f"ai-video/outputs/{task_id}.jpg")
        if thumb_blob.exists():
            thumb_blob.delete()
    except Exception as e:
        logger.warning(f"GCS清理失败: {e}")

    return {"message": "任务删除成功", "task_id": task_id}


@router.get("/download/{task_id}", tags=["AI Video"])
async def download_video(task_id: str):
    """
    获取视频的签名下载链接（有效期1小时）

    - **task_id**: 任务ID
    """
    task = await ai_video_service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in (VideoGenerationStatus.COMPLETED, "completed"):
        raise HTTPException(status_code=400, detail="任务尚未完成")

    try:
        from google.cloud import storage as gcs_storage
        from datetime import timedelta

        bucket_name = settings.fission_upload_bucket or "vigloo-fission-uploads"
        blob_name = f"ai-video/outputs/{task_id}.mp4"

        storage_client = gcs_storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if not blob.exists():
            raise HTTPException(
                status_code=404,
                detail="视频文件尚未生成或不存在（当前为模拟任务，未接入实际AI视频生成API）"
            )

        download_filename = f"video_{task_id[:8]}.mp4"
        download_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
            response_disposition=f'attachment; filename="{download_filename}"',
            response_type="video/mp4",
        )
        return {"download_url": download_url, "expires_in": 3600}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成视频下载链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

