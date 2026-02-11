"""字幕生成模块数据模型"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime


class LanguageCode(str, Enum):
    """支持的语言代码"""
    ZH = "zh"
    ZH_TW = "zh-TW"
    EN = "en"
    JA = "ja"
    KO = "ko"
    ES = "es"
    ID = "id"
    AR = "ar"
    TH = "th"
    VI = "vi"
    FR = "fr"
    DE = "de"
    PT = "pt"
    RU = "ru"


class SubtitleFormat(str, Enum):
    """字幕格式"""
    SRT = "srt"
    ASS = "ass"


class ProcessStatus(str, Enum):
    """处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubtitleSegment(BaseModel):
    """字幕片段"""
    index: int
    start_time: float
    end_time: float
    text: str
    confidence: Optional[float] = None


class TranscriptionResult(BaseModel):
    """转录结果"""
    language: str
    language_probability: float
    duration: float
    segments: List[SubtitleSegment]
    text: str


class TranslationResult(BaseModel):
    """翻译结果"""
    source_language: str
    target_language: str
    segments: List[SubtitleSegment]


class SubtitleFileInfo(BaseModel):
    """字幕文件信息"""
    language: str
    format: SubtitleFormat
    file_path: str
    file_size: int


class SubtitleTask(BaseModel):
    """字幕处理任务"""
    task_id: str
    filename: str
    status: ProcessStatus
    progress: float = 0.0
    source_language: Optional[str] = None
    target_languages: List[str]
    created_by: str  # 用户ID
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    transcription: Optional[TranscriptionResult] = None
    translations: Optional[Dict[str, TranslationResult]] = None
    subtitle_files: Optional[List[SubtitleFileInfo]] = None


class SubtitleTaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    message: str
    status: ProcessStatus


class SubtitleTaskStatusResponse(BaseModel):
    """任务状态响应"""
    task: SubtitleTask
