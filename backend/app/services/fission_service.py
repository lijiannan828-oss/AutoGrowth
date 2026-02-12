"""Fission (裂变素材生成) service."""

from __future__ import annotations

import os
import random
from typing import List, Optional, Tuple

from google.cloud import run_v2, storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.config import settings
from app.core.firestore import get_firestore_client
from app.schemas.auth import AuthenticatedUser
from app.schemas.fission import (
    FissionJobRequest,
    FissionJobDetail,
    FissionJobListItem,
    StickerAsset,
    TransformConfig,
    VariantInfo,
    FilterPreset,
)


class FissionService:
    """裂变素材生成服务"""

    def __init__(self) -> None:
        try:
            self._firestore = get_firestore_client()
        except RuntimeError as e:
            raise RuntimeError(
                f"Fission 服务初始化失败：{e}\n"
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

        self._jobs_collection = "fission_jobs"
        self._stickers_collection = "fission_stickers"

    def create_fission_job(
        self,
        request: FissionJobRequest,
        current_user: AuthenticatedUser,
    ) -> str:
        """创建裂变任务"""
        # 验证源视频路径
        self._validate_source_video(request.source_video_path)

        # 创建 Firestore 文档
        job_ref = self._firestore.collection(self._jobs_collection).document()
        job_data = {
            "drama_name": request.drama_name,
            "source_video_path": request.source_video_path,
            "variant_count": request.variant_count,
            "transforms": [t.model_dump() for t in request.transforms],
            "max_output_size_mb": request.max_output_size_mb,
            "duration_variance_percent": request.duration_variance_percent,
            "status": "QUEUED",
            "progress": 0,
            "progress_text": "任务已创建，等待处理",
            "variants": [],
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
            "created_by": current_user.email,
            "created_by_name": current_user.name or current_user.email,
        }

        # 添加贴纸配置（如果有）
        if request.sticker_config:
            job_data["sticker_config"] = request.sticker_config.model_dump()

        job_ref.set(job_data)

        # 触发 Cloud Run Job (Worker) - 并行处理
        try:
            # 每个变体一个独立 task，全量并行处理
            variant_count = request.variant_count
            task_count = variant_count

            self._trigger_fission_worker(job_ref.id, task_count)
        except Exception as e:
            # 如果触发失败，记录错误但不阻止任务创建
            print(f"Warning: Failed to trigger worker for job {job_ref.id}: {e}")

        return job_ref.id

    def list_fission_jobs(
        self,
        status: Optional[str] = None,
        drama_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[FissionJobListItem], int]:
        """获取裂变任务列表（支持分页）"""
        from datetime import datetime, timezone, timedelta

        query = self._firestore.collection(self._jobs_collection)

        # 按状态筛选
        if status:
            query = query.where("status", "==", status.upper())

        # 按剧集名称筛选
        if drama_name:
            query = query.where("drama_name", "==", drama_name)

        # 按创建时间倒序
        query = query.order_by("created_at", direction="DESCENDING")

        # 获取总数（用于分页）
        all_docs = list(query.stream())
        total = len(all_docs)

        now = datetime.now(timezone.utc)
        stale_timeout = timedelta(hours=1)

        # 统计进度>=80%的任务数 + 自动标记超时任务为 FAILED
        completed_count = 0
        overridden = {}  # doc.id -> 被修正的字段，供分页循环使用
        for doc in all_docs:
            data = doc.to_dict() or {}
            try:
                p = data.get("progress", 0)
                if int(p) >= 80:
                    completed_count += 1
            except (ValueError, TypeError):
                pass

            # 超时检测：PROCESSING + 进度 0% + 超过 1 小时未更新 → 自动标记 FAILED
            if data.get("status") == "PROCESSING" and int(data.get("progress", 0)) == 0:
                updated_at = data.get("updated_at")
                if updated_at and hasattr(updated_at, "timestamp"):
                    elapsed = now - updated_at.replace(tzinfo=timezone.utc) if updated_at.tzinfo is None else now - updated_at
                    if elapsed > stale_timeout:
                        try:
                            doc.reference.update({
                                "status": "FAILED",
                                "error_message": "处理超时：任务启动超过1小时仍无进度，已自动标记失败",
                                "updated_at": SERVER_TIMESTAMP,
                            })
                            overridden[doc.id] = {
                                "status": "FAILED",
                                "error_message": "处理超时：任务启动超过1小时仍无进度，已自动标记失败",
                            }
                        except Exception as e:
                            print(f"[WARN] 自动标记超时任务失败: {doc.id}: {e}")

        # 分页
        offset = (page - 1) * page_size
        paginated_docs = all_docs[offset:offset + page_size]

        jobs = []
        for doc in paginated_docs:
            data = doc.to_dict() or {}
            # 应用本次请求中被修正的字段
            if doc.id in overridden:
                data.update(overridden[doc.id])
            jobs.append(
                FissionJobListItem(
                    job_id=doc.id,
                    drama_name=data.get("drama_name", ""),
                    variant_count=data.get("variant_count", 0),
                    status=data.get("status", "UNKNOWN"),
                    progress=data.get("progress", 0),
                    created_at=data.get("created_at"),
                    created_by=data.get("created_by"),
                    error_message=data.get("error_message"),
                )
            )

        return jobs, total, completed_count

    def get_fission_job(self, job_id: str) -> Optional[FissionJobDetail]:
        """获取裂变任务详情"""
        doc_ref = self._firestore.collection(self._jobs_collection).document(job_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict() or {}

        # 解析变换配置
        transforms = [
            TransformConfig(**t) for t in data.get("transforms", [])
        ]

        # 解析变体信息并生成签名 URL
        variants = []
        for v in data.get("variants", []):
            variant_data = dict(v)

            # 为缩略图生成签名 URL
            if variant_data.get("thumbnail_path"):
                thumbnail_url = self._generate_signed_url(variant_data["thumbnail_path"])
                if thumbnail_url:
                    variant_data["thumbnail_path"] = thumbnail_url

            variants.append(VariantInfo(**variant_data))

        return FissionJobDetail(
            job_id=doc.id,
            drama_name=data.get("drama_name", ""),
            source_video_path=data.get("source_video_path", ""),
            variant_count=data.get("variant_count", 0),
            transforms=transforms,
            status=data.get("status", "UNKNOWN"),
            progress=data.get("progress", 0),
            progress_text=data.get("progress_text"),
            variants=variants,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            created_by=data.get("created_by"),
            error_message=data.get("error_message"),
        )

    def _generate_signed_url(self, gcs_path: str, expiration_hours: int = 1) -> Optional[str]:
        """生成 GCS 签名 URL"""
        if not gcs_path or not gcs_path.startswith("gs://"):
            return None

        try:
            path_parts = gcs_path[5:].split("/", 1)
            if len(path_parts) != 2:
                return None

            bucket_name, blob_name = path_parts
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            from datetime import timedelta
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=expiration_hours),
                method="GET",
            )
            return url
        except Exception as e:
            print(f"[ERROR] Failed to generate signed URL for {gcs_path}: {e}")
            return None

    def generate_download_url(self, job_id: str, variant_id: str) -> Optional[str]:
        """生成变体的签名下载链接（有效期1小时）"""
        # 获取任务详情
        job = self.get_fission_job(job_id)
        if not job:
            return None

        # 查找对应的变体
        variant = None
        for v in job.variants:
            if v.variant_id == variant_id:
                variant = v
                break

        if not variant:
            return None

        # 生成签名 URL（强制下载）
        gcs_path = variant.output_path
        if not gcs_path or not gcs_path.startswith("gs://"):
            return None

        try:
            path_parts = gcs_path[5:].split("/", 1)
            if len(path_parts) != 2:
                return None

            bucket_name, blob_name = path_parts
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            from datetime import timedelta
            # 生成文件名
            filename = f"{job.drama_name}_{variant_id}.mp4"

            # 生成签名 URL，指定 Content-Disposition 为 attachment（强制下载）
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=1),
                method="GET",
                response_disposition=f'attachment; filename="{filename}"',
                response_type="video/mp4",
            )
            return url
        except Exception as e:
            print(f"[ERROR] Failed to generate download URL: {e}")
            return None

    def retry_fission_job(self, job_id: str) -> bool:
        """重试失败的裂变任务：重置状态并重新触发 Worker"""
        doc_ref = self._firestore.collection(self._jobs_collection).document(job_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        data = doc.to_dict() or {}
        status = data.get("status", "")

        if status not in ["FAILED", "QUEUED"]:
            return False

        variant_count = data.get("variant_count", 5)
        if variant_count <= 5:
            task_count = 1
        elif variant_count <= 15:
            task_count = 2
        else:
            task_count = 3

        doc_ref.update({
            "status": "QUEUED",
            "progress": 0,
            "progress_text": "任务已重置，等待处理",
            "error_message": None,
            "variants": [],
            "updated_at": SERVER_TIMESTAMP,
        })

        try:
            self._trigger_fission_worker(job_id, task_count)
        except Exception as e:
            print(f"[WARNING] Retry trigger failed for job {job_id}: {e}")

        return True

    def cancel_fission_job(self, job_id: str) -> bool:
        """取消裂变任务"""
        doc_ref = self._firestore.collection(self._jobs_collection).document(job_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        data = doc.to_dict() or {}
        status = data.get("status", "")

        # 只能取消 QUEUED 或 PROCESSING 状态的任务
        if status not in ["QUEUED", "PROCESSING"]:
            return False

        doc_ref.update({
            "status": "CANCELLED",
            "progress_text": "任务已取消",
            "updated_at": SERVER_TIMESTAMP,
        })

        return True

    def list_stickers(self, category: Optional[str] = None) -> List[StickerAsset]:
        """获取贴纸素材列表"""
        query = self._firestore.collection(self._stickers_collection)

        if category:
            query = query.where("category", "==", category)

        docs = query.stream()
        stickers = []

        for doc in docs:
            data = doc.to_dict() or {}
            stickers.append(
                StickerAsset(
                    sticker_id=doc.id,
                    name=data.get("name", ""),
                    category=data.get("category", ""),
                    gcs_path=data.get("gcs_path", ""),
                    thumbnail_path=data.get("thumbnail_path"),
                    animation_type=data.get("animation_type", "static"),
                )
            )

        return stickers

    def _validate_source_video(self, gcs_path: str) -> None:
        """验证源视频是否存在"""
        if not gcs_path.startswith("gs://"):
            raise ValueError("源视频路径必须是GCS路径（gs://...）")

        # 解析GCS路径
        path_parts = gcs_path[5:].split("/", 1)
        if len(path_parts) != 2:
            raise ValueError("无效的GCS路径格式")

        bucket_name, blob_name = path_parts

        try:
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            if not blob.exists():
                raise ValueError(f"源视频不存在: {gcs_path}")
        except Exception as e:
            raise ValueError(f"验证源视频失败: {str(e)}")

    def _trigger_fission_worker(self, job_id: str, task_count: int = 1) -> None:
        """触发Cloud Run Job执行裂变任务 - 支持并行"""
        try:
            # Cloud Run Job配置
            project_id = os.getenv("GCP_PROJECT_ID", "fleet-blend-469520-n7")
            location = os.getenv("GCP_REGION", "us-central1")
            job_name = "fission-worker"

            # 构建Job路径
            parent = f"projects/{project_id}/locations/{location}"
            job_path = f"{parent}/jobs/{job_name}"

            print(f"[INFO] Triggering {task_count} parallel tasks for job {job_id}")

            # 创建执行请求 - 设置并行任务数
            # 注意：必须保留 -m app.workers.fission.main 参数，然后追加 job_id
            request = run_v2.RunJobRequest(
                name=job_path,
                overrides=run_v2.RunJobRequest.Overrides(
                    task_count=task_count,  # 设置并行任务数
                    container_overrides=[
                        run_v2.RunJobRequest.Overrides.ContainerOverride(
                            args=["-m", "app.workers.fission.main", job_id]
                        )
                    ]
                )
            )

            # 触发Job
            operation = self._jobs_client.run_job(request=request)

            # 更新任务状态
            self._firestore.collection(self._jobs_collection).document(job_id).update({
                "cloud_run_execution": operation.name,
                "updated_at": SERVER_TIMESTAMP,
            })

        except Exception as e:
            # 如果触发失败，记录错误但保持QUEUED状态，允许重试
            print(f"[WARNING] Failed to trigger worker for job {job_id}: {e}")
            self._firestore.collection(self._jobs_collection).document(job_id).update({
                "progress_text": f"等待处理中（触发延迟）",
                "updated_at": SERVER_TIMESTAMP,
            })
            # 不抛出异常，让任务保持在队列中

    def create_batch_fission_jobs(
        self,
        source_videos: List[str],
        drama_name: str,
        transforms: List[TransformConfig],
        variant_count: int = 5,
        current_user: AuthenticatedUser = None,
    ) -> List[str]:
        """批量创建裂变任务"""
        job_ids = []

        for video_path in source_videos:
            request = FissionJobRequest(
                source_video_path=video_path,
                drama_name=drama_name,
                variant_count=variant_count,
                transforms=transforms,
            )

            job_id = self.create_fission_job(request, current_user)
            job_ids.append(job_id)

        return job_ids

    def get_preset_transforms(self, preset_name: str) -> List[TransformConfig]:
        """获取预设的变换配置"""
        presets = {
            "light": [
                TransformConfig(type="filter", enabled=True, params={"preset": "warm"}),
                TransformConfig(type="duration_adjust", enabled=True, params={}),
            ],
            "medium": [
                TransformConfig(type="filter", enabled=True, params={"preset": "cool"}),
                TransformConfig(type="duration_adjust", enabled=True, params={}),
                TransformConfig(type="frame_shuffle", enabled=True, params={"intensity": 0.2}),
            ],
            "heavy": [
                TransformConfig(type="filter", enabled=True, params={"preset": "vintage"}),
                TransformConfig(type="duration_adjust", enabled=True, params={}),
                TransformConfig(type="frame_shuffle", enabled=True, params={"intensity": 0.4}),
                TransformConfig(type="sticker_overlay", enabled=True, params={}),
            ],
        }

        return presets.get(preset_name, presets["medium"])
