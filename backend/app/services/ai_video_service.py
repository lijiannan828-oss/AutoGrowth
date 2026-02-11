"""AI 视频生成服务（Firestore + Cloud Run Job 架构，与裂变模块一致）。

任务元数据存储在 Firestore 集合 ``ai_video_jobs`` 中。
生成的视频和缩略图存储在 GCS 存储桶：
  桶名: vigloo-fission-uploads (由 settings.fission_upload_bucket 配置)
  路径: ai-video/outputs/{task_id}.mp4   (视频)
        ai-video/outputs/{task_id}.jpg   (缩略图)

后台处理由 Cloud Run Job ``ai-video-worker`` 执行（与裂变模块相同模式）。
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from google.cloud import run_v2, storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.config import settings
from app.core.firestore import get_firestore_client
from app.schemas.ai_video import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoGenerationStatus,
    VideoTaskStatus,
    VideoStyle,
)

logger = logging.getLogger(__name__)


class AIVideoService:
    """AI 视频生成服务（与裂变模块架构一致：Firestore + Cloud Run Job）。"""

    def __init__(self) -> None:
        try:
            self._firestore = get_firestore_client()
        except RuntimeError as e:
            raise RuntimeError(
                f"AI Video 服务初始化失败：{e}\n"
                "请确保已配置 FIRESTORE_PROJECT_ID 环境变量或 GCP_PROJECT_ID"
            )

        try:
            self._storage_client = storage.Client()
        except Exception as e:
            raise RuntimeError(
                f"GCS 客户端初始化失败：{e}\n"
                "请确保已配置 Google Cloud 凭证 (GOOGLE_APPLICATION_CREDENTIALS)"
            )

        try:
            self._jobs_client = run_v2.JobsClient()
        except Exception as e:
            raise RuntimeError(
                f"Cloud Run Jobs 客户端初始化失败：{e}\n"
                "请确保已配置 Google Cloud 凭证和项目权限"
            )

        self._jobs_collection = "ai_video_jobs"

        # 内存缓存（兼容旧的 delete 路由访问 self.tasks）
        self.tasks: dict[str, dict] = {}

    # ------------------------------------------------------------------ 公开 API

    async def generate_video(
        self, request: VideoGenerationRequest
    ) -> VideoGenerationResponse:
        """创建视频生成任务 → 写入 Firestore → 触发 Cloud Run Job。"""

        task_id = str(uuid.uuid4())
        now_iso = datetime.utcnow().isoformat()

        # 构建完整提示词（用于 Worker）
        full_prompt = self._build_full_prompt(request)

        # 写入 Firestore
        doc_ref = self._firestore.collection(self._jobs_collection).document(task_id)
        doc_data = {
            "task_id": task_id,
            "status": VideoGenerationStatus.PENDING.value,
            "progress": 0,
            "progress_text": "任务已创建，等待处理",
            "prompt": request.prompt,
            "full_prompt": full_prompt,
            "style": request.style.value,
            "duration": request.duration,
            "aspect_ratio": request.aspect_ratio.value,
            "character_description": request.character_description,
            "scene_description": request.scene_description,
            "camera_movement": request.camera_movement,
            "audio_style": request.audio_style,
            "video_url": None,
            "thumbnail_url": None,
            "video_gcs_path": None,
            "thumbnail_gcs_path": None,
            "error_message": None,
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
            "completed_at": None,
        }
        doc_ref.set(doc_data)
        logger.info(f"AI Video 任务已写入 Firestore: {task_id}")

        # 触发 Cloud Run Job（与裂变模块一致）
        try:
            self._trigger_worker(task_id)
        except Exception as e:
            logger.warning(f"触发 AI Video Worker 失败: {e}")

        # 估算时间
        estimated_time = self._estimate_generation_time(request)

        return VideoGenerationResponse(
            task_id=task_id,
            status=VideoGenerationStatus.PENDING,
            message="视频生成任务已创建，正在处理中",
            estimated_time=estimated_time,
        )

    async def get_task_status(self, task_id: str) -> Optional[VideoTaskStatus]:
        """从 Firestore 获取任务状态，并对已完成任务刷新签名 URL。"""

        doc_ref = self._firestore.collection(self._jobs_collection).document(task_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None

        data = doc.to_dict() or {}

        # 刷新签名 URL（签名有效期1小时）
        video_url = data.get("video_url")
        thumbnail_url = data.get("thumbnail_url")
        status_val = data.get("status", "")

        if status_val in (VideoGenerationStatus.COMPLETED.value, "completed"):
            if data.get("video_gcs_path"):
                bucket_name = settings.fission_upload_bucket or "vigloo-fission-uploads"
                video_blob = f"ai-video/outputs/{task_id}.mp4"
                thumb_blob = f"ai-video/outputs/{task_id}.jpg"
                video_url = self._generate_signed_url(bucket_name, video_blob) or video_url
                thumbnail_url = self._generate_signed_url(bucket_name, thumb_blob) or thumbnail_url

        # 处理 Firestore Timestamp 类型
        created_at = data.get("created_at")
        completed_at = data.get("completed_at")
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        if hasattr(completed_at, "isoformat"):
            completed_at = completed_at.isoformat()

        return VideoTaskStatus(
            task_id=data.get("task_id", task_id),
            status=status_val,
            progress=data.get("progress", 0),
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            error_message=data.get("error_message"),
            created_at=created_at or "",
            completed_at=completed_at,
        )

    async def list_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[VideoGenerationStatus] = None,
    ) -> dict:
        """从 Firestore 获取任务列表（分页、筛选）。"""

        query = self._firestore.collection(self._jobs_collection)

        if status:
            query = query.where("status", "==", status.value)

        # 按创建时间倒序
        query = query.order_by("created_at", direction="DESCENDING")

        all_docs = list(query.stream())
        total = len(all_docs)

        # 分页
        offset = (page - 1) * page_size
        paginated_docs = all_docs[offset : offset + page_size]

        items = []
        for doc in paginated_docs:
            data = doc.to_dict() or {}
            created_at = data.get("created_at")
            completed_at = data.get("completed_at")
            if hasattr(created_at, "isoformat"):
                created_at = created_at.isoformat()
            if hasattr(completed_at, "isoformat"):
                completed_at = completed_at.isoformat()

            items.append(
                VideoTaskStatus(
                    task_id=data.get("task_id", doc.id),
                    status=data.get("status", "pending"),
                    progress=data.get("progress", 0),
                    video_url=data.get("video_url"),
                    thumbnail_url=data.get("thumbnail_url"),
                    error_message=data.get("error_message"),
                    created_at=created_at or "",
                    completed_at=completed_at,
                )
            )

        return {
            "total": total,
            "items": items,
            "page": page,
            "page_size": page_size,
        }

    # ----------------------------------------------- 内部方法：Cloud Run Job 触发

    def _trigger_worker(self, task_id: str) -> None:
        """触发 Cloud Run Job 执行 AI 视频生成（与裂变模块一致）。"""
        try:
            project_id = os.getenv("GCP_PROJECT_ID", "fleet-blend-469520-n7")
            location = os.getenv("GCP_REGION", "us-central1")
            job_name = "ai-video-worker"

            parent = f"projects/{project_id}/locations/{location}"
            job_path = f"{parent}/jobs/{job_name}"

            logger.info(f"[AI Video] 触发 Cloud Run Job: {job_path}, task_id={task_id}")

            request = run_v2.RunJobRequest(
                name=job_path,
                overrides=run_v2.RunJobRequest.Overrides(
                    task_count=1,
                    container_overrides=[
                        run_v2.RunJobRequest.Overrides.ContainerOverride(
                            args=["-m", "app.workers.ai_video.main", task_id]
                        )
                    ],
                ),
            )

            operation = self._jobs_client.run_job(request=request)

            # 记录 Cloud Run 执行信息
            self._firestore.collection(self._jobs_collection).document(task_id).update(
                {
                    "cloud_run_execution": operation.name,
                    "updated_at": SERVER_TIMESTAMP,
                }
            )

        except Exception as e:
            logger.warning(f"[AI Video] 触发 Worker 失败: {e}")
            self._firestore.collection(self._jobs_collection).document(task_id).update(
                {
                    "progress_text": "等待处理中（触发延迟）",
                    "updated_at": SERVER_TIMESTAMP,
                }
            )

    # ----------------------------------------------- 内部方法：提示词 & 估算

    @staticmethod
    def _build_full_prompt(request: VideoGenerationRequest) -> str:
        """根据请求构建完整提示词。"""
        parts = [request.prompt]

        if request.character_description:
            parts.append(f"人物: {request.character_description}")
        if request.scene_description:
            parts.append(f"场景: {request.scene_description}")
        if request.camera_movement:
            parts.append(f"镜头: {request.camera_movement}")
        if request.audio_style:
            parts.append(f"音频: {request.audio_style}")

        parts.append(f"风格: {request.style.value}")
        parts.append(f"时长: {request.duration}秒")
        parts.append(f"比例: {request.aspect_ratio.value}")

        return " | ".join(parts)

    @staticmethod
    def _estimate_generation_time(request: VideoGenerationRequest) -> int:
        """估算视频生成时间（秒）。"""
        base_time = 30
        duration_factor = request.duration * 2
        style_factor = {
            VideoStyle.REALISTIC: 1.5,
            VideoStyle.ANIME: 1.2,
            VideoStyle.DRAMA: 1.3,
            VideoStyle.CINEMATIC: 1.6,
            VideoStyle.CARTOON: 1.0,
        }.get(request.style, 1.0)
        return int(base_time + duration_factor * style_factor)

    # ----------------------------------------------- 内部方法：签名 URL

    def _generate_signed_url(
        self, bucket_name: str, blob_name: str, expiration_hours: int = 1
    ) -> Optional[str]:
        """生成 GCS 签名 URL（与裂变模块一致）。"""
        try:
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=expiration_hours),
                method="GET",
            )
            return url
        except Exception as e:
            logger.warning(f"生成签名URL失败 ({blob_name}): {e}")
            return None
