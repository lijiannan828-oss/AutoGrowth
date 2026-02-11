"""视频元数据管理服务"""

from __future__ import annotations

from typing import Optional, List
from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from app.core.firestore import get_firestore_client

COLLECTION_NAME = "fission_videos"


class VideoMetadataService:
    """视频元数据管理服务"""

    def __init__(self):
        self.firestore = get_firestore_client()
        self.collection = self.firestore.collection(COLLECTION_NAME)

    def create_video_metadata(
        self,
        user_id: str,
        gcs_path: str,
        gcs_bucket: str,
        gcs_blob_name: str,
        display_name: str,
        original_filename: str,
        file_size: int,
        content_type: str,
        file_extension: str,
    ) -> str:
        """创建视频元数据

        Args:
            user_id: 用户 ID
            gcs_path: GCS 完整路径
            gcs_bucket: GCS 桶名
            gcs_blob_name: blob 名称
            display_name: 用户自定义显示名称
            original_filename: 原始上传文件名
            file_size: 文件大小（字节）
            content_type: MIME 类型
            file_extension: 文件扩展名

        Returns:
            创建的文档 ID
        """
        doc_ref = self.collection.document()
        doc_data = {
            "user_id": user_id,
            "gcs_path": gcs_path,
            "gcs_bucket": gcs_bucket,
            "gcs_blob_name": gcs_blob_name,
            "display_name": display_name,
            "original_filename": original_filename,
            "file_size": file_size,
            "content_type": content_type,
            "file_extension": file_extension,
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
            "status": "active",
        }
        doc_ref.set(doc_data)
        return doc_ref.id

    def get_video_by_gcs_path(self, gcs_path: str) -> Optional[dict]:
        """根据 GCS 路径查询视频元数据

        Args:
            gcs_path: GCS 完整路径

        Returns:
            视频元数据字典，如果不存在则返回 None
        """
        query = (
            self.collection
            .where("gcs_path", "==", gcs_path)
            .where("status", "==", "active")
            .limit(1)
        )
        docs = list(query.stream())
        if docs:
            data = docs[0].to_dict()
            data["video_id"] = docs[0].id
            return data
        return None

    def list_user_videos(self, user_id: str) -> List[dict]:
        """列出用户的所有视频

        Args:
            user_id: 用户 ID

        Returns:
            视频元数据列表
        """
        query = (
            self.collection
            .where("user_id", "==", user_id)
            .where("status", "==", "active")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
        )
        videos = []
        for doc in query.stream():
            data = doc.to_dict()
            data["video_id"] = doc.id
            videos.append(data)
        return videos

    def update_display_name(self, video_id: str, user_id: str, display_name: str) -> bool:
        """更新视频显示名称

        Args:
            video_id: 视频文档 ID
            user_id: 用户 ID（用于权限验证）
            display_name: 新的显示名称

        Returns:
            是否更新成功

        Raises:
            PermissionError: 如果用户无权修改此视频
        """
        doc_ref = self.collection.document(video_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False

        data = doc.to_dict()
        if data.get("user_id") != user_id:
            raise PermissionError("无权修改此视频")

        doc_ref.update({
            "display_name": display_name,
            "updated_at": SERVER_TIMESTAMP,
        })
        return True
