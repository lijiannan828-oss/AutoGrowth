"""Fission (裂变素材生成) related schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TransformType(str, Enum):
    """变换类型枚举"""
    FILTER = "filter"  # 滤镜处理
    FRAME_SHUFFLE = "frame_shuffle"  # 抽帧重组
    DURATION_ADJUST = "duration_adjust"  # 时长调整
    STICKER_OVERLAY = "sticker_overlay"  # 贴纸叠加


class FilterPreset(str, Enum):
    """滤镜预设枚举"""
    WARM = "warm"  # 暖色调
    COOL = "cool"  # 冷色调
    VINTAGE = "vintage"  # 复古
    HIGH_CONTRAST = "high_contrast"  # 高对比度
    SOFT = "soft"  # 柔和


class TransformConfig(BaseModel):
    """单个变换配置"""
    type: TransformType = Field(..., description="变换类型")
    enabled: bool = Field(default=True, description="是否启用")
    params: Dict[str, Any] = Field(default_factory=dict, description="变换参数")


class StickerPosition(BaseModel):
    """贴纸位置配置"""
    x_percent: float = Field(default=50, ge=0, le=100, description="X 位置百分比")
    y_percent: float = Field(default=50, ge=0, le=100, description="Y 位置百分比")
    scale: float = Field(default=1.0, ge=0.1, le=3.0, description="缩放比例")


class StickerConfig(BaseModel):
    """贴纸配置"""
    sticker_id: str = Field(..., description="贴纸素材 ID")
    position: StickerPosition = Field(default_factory=StickerPosition)
    start_time: Optional[float] = Field(None, description="开始时间（秒）")
    end_time: Optional[float] = Field(None, description="结束时间（秒）")


# ==================== 请求/响应模型 ====================

class FissionJobRequest(BaseModel):
    """创建裂变任务请求"""
    source_video_path: str = Field(..., description="源视频 GCS 路径")
    drama_name: str = Field(..., description="剧集名称")
    variant_count: int = Field(default=5, ge=1, le=10, description="生成变体数量")
    transforms: List[TransformConfig] = Field(..., description="变换配置列表")
    max_output_size_mb: int = Field(default=500, le=500, description="最大输出大小(MB)")
    duration_variance_percent: int = Field(default=20, ge=0, le=30, description="时长变化百分比")
    sticker_config: Optional[StickerConfig] = Field(None, description="贴纸配置")

    @field_validator("transforms")
    @classmethod
    def validate_transforms(cls, value: List[TransformConfig]) -> List[TransformConfig]:
        enabled = [t for t in value if t.enabled]
        if not enabled:
            raise ValueError("至少需要启用一种变换")
        return value


class FissionJobResponse(BaseModel):
    """创建裂变任务响应"""
    job_id: str = Field(..., description="任务 ID")
    status: str = Field(default="QUEUED", description="任务状态")


class VariantInfo(BaseModel):
    """变体信息"""
    variant_id: str = Field(..., description="变体 ID")
    output_path: str = Field(..., description="输出 GCS 路径")
    file_size_bytes: int = Field(..., description="文件大小(字节)")
    duration_seconds: float = Field(..., description="时长(秒)")
    transforms_applied: List[str] = Field(..., description="应用的变换列表")
    thumbnail_path: Optional[str] = Field(None, description="缩略图路径")


class FissionJobDetail(BaseModel):
    """裂变任务详情"""
    job_id: str
    drama_name: str
    source_video_path: str
    variant_count: int
    transforms: List[TransformConfig]
    status: str
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比")
    progress_text: Optional[str] = None
    variants: List[VariantInfo] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    error_message: Optional[str] = None


class FissionJobListItem(BaseModel):
    """裂变任务列表项"""
    job_id: str
    drama_name: str
    variant_count: int
    status: str
    progress: int = 0
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    error_message: Optional[str] = None


class FissionJobsListResponse(BaseModel):
    """裂变任务列表响应"""
    jobs: List[FissionJobListItem]
    total: int
    completed_count: int = 0


# ==================== 贴纸素材模型 ====================

class StickerAsset(BaseModel):
    """贴纸素材"""
    sticker_id: str
    name: str
    category: str = Field(..., description="分类: emoji, text, effect, brand")
    gcs_path: str
    thumbnail_path: Optional[str] = None
    animation_type: str = Field(default="static", description="动画类型: static, animated")


class StickerListResponse(BaseModel):
    """贴纸列表响应"""
    stickers: List[StickerAsset]


# ==================== 视频元数据模型 ====================

class VideoMetadata(BaseModel):
    """视频元数据模型"""
    video_id: str
    user_id: str
    gcs_path: str
    gcs_bucket: str
    gcs_blob_name: str
    display_name: str
    original_filename: str
    file_size: int
    content_type: str
    file_extension: str
    created_at: datetime
    updated_at: datetime
    status: str = "active"


class VideoUploadResponse(BaseModel):
    """视频上传响应"""
    video_id: str
    filename: str = Field(..., description="UUID 文件名（兼容）")
    display_name: str
    original_filename: str
    gcs_path: str
    size: int


class VideoListItem(BaseModel):
    """视频列表项"""
    video_id: str
    name: str = Field(..., description="UUID 文件名（兼容旧代码）")
    display_name: Optional[str] = None
    original_filename: Optional[str] = None
    gcs_path: str
    size: int
    updated: Optional[str] = None


class VideoRenameRequest(BaseModel):
    """视频重命名请求"""
    display_name: str = Field(..., min_length=1, max_length=100)
