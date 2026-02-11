"\"\"\"Pipeline related schemas.\"\"\""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class PipelineFolder(BaseModel):
    id: str = Field(..., description="Google Drive folder ID")
    name: str
    files_total: Optional[int] = Field(None, description="GDrive 文件总数（统计）")
    files_in_gcs: Optional[int] = Field(None, description="GCS 已同步文件数")
    children: Optional[List["PipelineFolder"]] = Field(default=None, description="子目录")


class GDriveProgramStatus(BaseModel):
    name: str
    path: str
    gdrive_id: str
    in_gcs: bool
    files_total: Optional[int] = None
    files_in_gcs: Optional[int] = None
    updated_at: Optional[datetime] = None
    total_size_bytes: Optional[int] = None


class FolderBrowseNode(BaseModel):
    id: str = Field(..., description="Google Drive folder ID")
    name: str = Field(..., description="文件夹名称")
    has_children: bool = Field(default=True, description="是否可能存在子目录")
    in_gcs: bool = Field(default=False, description="GCS 中是否已存在对应目录")


class PipelineRoot(BaseModel):
    label: str = Field(..., description="根目录显示名称（KR/JP/US 等）")
    folder_id: str = Field(..., description="Google Drive 根目录 ID")


class TransferJobRequest(BaseModel):
    drama_name: str = Field(..., description="剧集 Program 名称/Code")
    gdrive_path: str = Field(..., description="GDrive 中的路径（含根目录）")
    include_folders: List[str] = Field(
        ..., description="需要传输的子目录，使用相对路径（如 Program/[Final]Episodes）"
    )


class TransferJobResponse(BaseModel):
    job_id: str = Field(..., description="新建 Firestore pipeline job 的文档 ID")
    status: str = Field(default="QUEUED", description="当前任务状态")


class ManualProcessRequest(BaseModel):
    drama_name: str = Field(..., description="剧集 Program 名称/Code")
    file_paths: List[str] = Field(
        ..., description="相对剧集根目录的文件/文件夹路径列表（例如 subtitles/[final]subtitles）"
    )

    @field_validator("file_paths")
    @classmethod
    def validate_file_paths(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("需至少提供一个文件/目录路径")
        return cleaned


class ManualProcessResponse(BaseModel):
    job_id: str = Field(..., description="触发的压制 Job ID")
    status: str = Field(default="QUEUED", description="当前状态")


class RetryProcessResponse(BaseModel):
    job_id: str = Field(..., description="触发的重试 Job ID")
    status: str = Field(default="QUEUED", description="当前状态")


class FailureDetail(BaseModel):
    stage: str = Field(..., description="失败阶段：transfer/process")
    file_path: str | None = Field(
        default=None, description="相关文件的 GCS/Drive 路径（若可用）"
    )
    error_message: str = Field(..., description="错误信息")


class TransferStatus(BaseModel):
    status: str | None = Field(default=None)
    progress_text: str | None = Field(default=None)


class ProcessStatus(BaseModel):
    status: str | None = Field(default=None)
    progress_text: str | None = Field(default=None)
    processed_count: int | None = Field(default=None)
    total_count: int | None = Field(default=None)
    language_details: dict[str, str | int | float] | None = Field(default=None)


class DramaJobRow(BaseModel):
    drama_name: str = Field(..., description="剧集名称")
    job_id: str = Field(..., description="对应的 pipeline_jobs 文档 ID")
    job_type: str | None = Field(default=None, description="任务类型（standard/retry 等）")
    source_path: str | None = Field(default=None, description="GDrive 源路径")
    transfer: TransferStatus = Field(default_factory=TransferStatus)
    process: ProcessStatus = Field(default_factory=ProcessStatus)
    failures: List[FailureDetail] = Field(default_factory=list)
    last_updated: datetime | None = Field(default=None)


class PipelineJobsResponse(BaseModel):
    items: List[DramaJobRow]


class PipelineJobsStatsResponse(BaseModel):
    in_progress_count: int = Field(..., description="进行中的任务数量（未标记结束）")
    transferring_count: int = Field(..., description="传输中任务数量")
    processing_count: int = Field(..., description="压制中任务数量（包括已传输完成在压制中 + 单独在压制）")
    failed_count: int = Field(..., description="失败任务数量")
    completed_count: int = Field(..., description="最近30天已完成任务数量")


class DownloadLinkResponse(BaseModel):
    url: str
    expires_at: datetime | None = None


class ZipDownloadRequest(BaseModel):
    paths: List[str]

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, value: List[str]) -> List[str]:
        filtered = [item.strip() for item in value if item and item.strip()]
        if not filtered:
            raise ValueError("至少需要提供一个 GCS 路径")
        return filtered


class ZipDownloadResponse(BaseModel):
    task_id: str
    status: str = Field(default="QUEUED")


class ZipTaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="任务状态：QUEUED/PROCESSING/COMPLETE/FAILED")
    status_message: str | None = Field(default=None, description="状态消息")
    progress: int | None = Field(default=None, description="进度百分比 (0-100)")
    download_url: str | None = Field(default=None, description="下载链接（完成时可用）")
    speed_bps: int | None = Field(default=None, description="下载速度（字节/秒）")
    estimated_seconds: int | None = Field(default=None, description="预计剩余时间（秒）")
    downloaded_bytes: int | None = Field(default=None, description="已下载字节数")
    total_bytes: int | None = Field(default=None, description="总字节数")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")


class NasDownloadRequest(BaseModel):
    drama_name: str | None = None
    files: List[str]
    notes: str | None = None

    @field_validator("files")
    @classmethod
    def validate_files(cls, value: List[str]) -> List[str]:
        filtered = [item.strip() for item in value if item and item.strip()]
        if not filtered:
            raise ValueError("需至少指定一个文件/目录路径")
        return filtered


class NasDownloadResponse(BaseModel):
    task_id: str
    status: str = Field(default="QUEUED")


class ZipTaskStatus(BaseModel):
    zip_gcs_path: str | None = None
    download_url: str | None = None
    status: str
    expires_at: datetime | None = None


PipelineFolder.model_rebuild()

