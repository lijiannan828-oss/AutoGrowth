"""
共享 GCS（Google Cloud Storage）工具函数

将各模块中重复出现的 GCS 操作（获取 bucket、上传、签名 URL 等）
集中到此处，消除跨模块重复代码。
"""

import logging
from datetime import timedelta
from typing import Optional, Tuple

from google.cloud import storage as gcs_storage

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 单例客户端（惰性初始化）
# ---------------------------------------------------------------------------

_storage_client: Optional[gcs_storage.Client] = None


def get_storage_client() -> gcs_storage.Client:
    """获取（或创建）单例 GCS 存储客户端"""
    global _storage_client
    if _storage_client is None:
        _storage_client = gcs_storage.Client()
    return _storage_client


def get_default_bucket_name() -> str:
    """返回项目默认的上传存储桶名"""
    return settings.fission_upload_bucket or "vigloo-fission-uploads"


def get_bucket(bucket_name: Optional[str] = None) -> Tuple[gcs_storage.Client, str]:
    """获取 GCS bucket 对象和 bucket 名称

    Returns:
        (bucket 对象, bucket_name)
    """
    name = bucket_name or get_default_bucket_name()
    client = get_storage_client()
    return client.bucket(name), name


# ---------------------------------------------------------------------------
# 上传
# ---------------------------------------------------------------------------


def upload_bytes(
    blob_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    bucket_name: Optional[str] = None,
) -> str:
    """将 bytes 数据上传到 GCS，返回 gs:// 路径"""
    bucket, bname = get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type=content_type)
    gcs_path = f"gs://{bname}/{blob_name}"
    logger.info(f"已上传到 GCS: {gcs_path}")
    return gcs_path


def upload_json(blob_name: str, data: str, bucket_name: Optional[str] = None) -> str:
    """上传 JSON 字符串到 GCS"""
    return upload_bytes(blob_name, data.encode("utf-8"), "application/json", bucket_name)


# ---------------------------------------------------------------------------
# 签名 URL
# ---------------------------------------------------------------------------


def generate_signed_url(
    blob_name: str,
    bucket_name: Optional[str] = None,
    expiration_hours: int = 1,
    method: str = "GET",
    response_disposition: Optional[str] = None,
    response_type: Optional[str] = None,
) -> str:
    """生成 GCS 签名 URL

    Raises:
        FileNotFoundError: 如果 blob 不存在且 check_exists=True
    """
    bucket, _ = get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    kwargs = {
        "version": "v4",
        "expiration": timedelta(hours=expiration_hours),
        "method": method,
    }
    if response_disposition:
        kwargs["response_disposition"] = response_disposition
    if response_type:
        kwargs["response_type"] = response_type

    return blob.generate_signed_url(**kwargs)


def generate_download_signed_url(
    blob_name: str,
    download_filename: str,
    content_type: str,
    bucket_name: Optional[str] = None,
    expiration_hours: int = 1,
) -> str:
    """生成强制下载的签名 URL（Content-Disposition: attachment）"""
    return generate_signed_url(
        blob_name=blob_name,
        bucket_name=bucket_name,
        expiration_hours=expiration_hours,
        response_disposition=f'attachment; filename="{download_filename}"',
        response_type=content_type,
    )


def blob_exists(blob_name: str, bucket_name: Optional[str] = None) -> bool:
    """检查 blob 是否存在"""
    bucket, _ = get_bucket(bucket_name)
    return bucket.blob(blob_name).exists()


# ---------------------------------------------------------------------------
# 解析 gs:// URI
# ---------------------------------------------------------------------------


def parse_gcs_uri(gcs_path: str) -> Tuple[str, str]:
    """解析 gs://bucket/blob 路径，返回 (bucket_name, blob_name)"""
    if not gcs_path or not gcs_path.startswith("gs://"):
        raise ValueError(f"无效的 GCS 路径: {gcs_path}")
    remainder = gcs_path[5:]
    if "/" not in remainder:
        raise ValueError(f"缺少对象路径: {gcs_path}")
    bucket_name, blob_name = remainder.split("/", 1)
    if not bucket_name or not blob_name:
        raise ValueError(f"缺少 bucket 或对象: {gcs_path}")
    return bucket_name, blob_name


def signed_url_from_gcs_path(
    gcs_path: str,
    expiration_hours: int = 1,
    response_disposition: Optional[str] = None,
    response_type: Optional[str] = None,
) -> Optional[str]:
    """从 gs:// 路径生成签名 URL，失败返回 None"""
    try:
        bucket_name, blob_name = parse_gcs_uri(gcs_path)
        return generate_signed_url(
            blob_name=blob_name,
            bucket_name=bucket_name,
            expiration_hours=expiration_hours,
            response_disposition=response_disposition,
            response_type=response_type,
        )
    except Exception as e:
        logger.warning(f"从 gs:// 路径生成签名 URL 失败 ({gcs_path}): {e}")
        return None

