"""AI Video generation schemas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class VideoStyle(str, Enum):
    """Video style options."""
    REALISTIC = "realistic"  # 真人写实风
    ANIME = "anime"  # 动漫风
    DRAMA = "drama"  # 短剧质感风
    CINEMATIC = "cinematic"  # 电影感
    CARTOON = "cartoon"  # 卡通风


class VideoAspectRatio(str, Enum):
    """Video aspect ratio options."""
    PORTRAIT = "9:16"  # 竖屏
    LANDSCAPE = "16:9"  # 横屏
    SQUARE = "1:1"  # 方形


class VideoGenerationStatus(str, Enum):
    """Video generation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoGenerationRequest(BaseModel):
    """Request schema for video generation."""
    prompt: str = Field(..., description="文字指令描述", min_length=10, max_length=2000)
    style: VideoStyle = Field(default=VideoStyle.REALISTIC, description="画风风格")
    duration: int = Field(default=5, ge=3, le=60, description="视频时长（秒）")
    aspect_ratio: VideoAspectRatio = Field(default=VideoAspectRatio.PORTRAIT, description="视频比例")
    
    # 可选的详细设定
    character_description: Optional[str] = Field(None, description="人物设定")
    scene_description: Optional[str] = Field(None, description="场景要求")
    camera_movement: Optional[str] = Field(None, description="镜头语言")
    audio_style: Optional[str] = Field(None, description="音频风格")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "一个年轻女孩在咖啡厅里看书，突然接到一个神秘电话，表情从平静变为惊讶",
                "style": "realistic",
                "duration": 10,
                "aspect_ratio": "9:16",
                "character_description": "20岁左右的亚洲女性，长发，穿着休闲",
                "scene_description": "温馨的咖啡厅，下午阳光透过窗户",
                "camera_movement": "从远景推进到中景特写",
                "audio_style": "轻柔的背景音乐，咖啡厅环境音"
            }
        }


class VideoGenerationResponse(BaseModel):
    """Response schema for video generation."""
    task_id: str = Field(..., description="任务ID")
    status: VideoGenerationStatus = Field(..., description="生成状态")
    message: str = Field(..., description="状态消息")
    estimated_time: Optional[int] = Field(None, description="预计完成时间（秒）")


class VideoTaskStatus(BaseModel):
    """Video task status schema."""
    task_id: str
    status: VideoGenerationStatus
    progress: int = Field(ge=0, le=100, description="进度百分比")
    video_url: Optional[str] = Field(None, description="生成的视频URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: str
    completed_at: Optional[str] = None


class VideoListResponse(BaseModel):
    """Video list response schema."""
    total: int
    items: list[VideoTaskStatus]
    page: int
    page_size: int

