"""字幕生成 API 路由

文件上传逻辑与裂变模块一致：
  1. POST /subtitle/upload  — 仅上传视频到 GCS + 创建 Firestore 元数据
  2. GET  /subtitle/videos  — 列出用户已上传的视频
  3. PATCH /subtitle/videos/{video_id} — 重命名视频
  4. POST /subtitle/tasks   — 从已上传视频创建字幕任务

存储路径:
  桶名: vigloo-fission-uploads (由 settings.subtitle_bucket 配置)
  视频: vigloo-subtitle-uploads/uploads/{user_id}/{uuid}.{ext}
  任务: vigloo-subtitle-uploads/tasks/{task_id}.json
  字幕: vigloo-subtitle-uploads/outputs/{task_id}/{lang}.{srt|ass}
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict

from fastapi import (
    APIRouter, UploadFile, File, Form, Query,
    HTTPException, BackgroundTasks, Depends, status,
)

from app.api.deps import get_current_user, AuthenticatedUser
from app.schemas.subtitle import (
    ProcessStatus,
    SubtitleTask,
    SubtitleTaskResponse,
    SubtitleTaskStatusResponse,
    SubtitleVideoUploadResponse,
    SubtitleVideoRenameRequest,
    SubtitleCreateTaskRequest,
)
from app.core.config import settings
from app.utils.gcs import (
    get_bucket,
    upload_bytes,
    upload_json,
    generate_download_signed_url,
    blob_exists,
)

router = APIRouter(prefix="/subtitle", tags=["subtitle"])
logger = logging.getLogger(__name__)

# 任务存储（同时持久化到GCS）
tasks: Dict[str, SubtitleTask] = {}
_subtitle_loaded_from_gcs = False


def _load_all_subtitle_tasks() -> None:
    """从 GCS 加载所有字幕任务元数据到内存"""
    global _subtitle_loaded_from_gcs
    if _subtitle_loaded_from_gcs:
        return
    _subtitle_loaded_from_gcs = True
    try:
        bucket, _ = get_bucket(settings.subtitle_bucket)
        blobs = bucket.list_blobs(prefix="vigloo-subtitle-uploads/tasks/")
        count = 0
        for blob in blobs:
            if blob.name.endswith(".json"):
                try:
                    data = json.loads(blob.download_as_text())
                    tid = data.get("task_id")
                    if tid and tid not in tasks:
                        tasks[tid] = SubtitleTask(**data)
                        count += 1
                except Exception as e:
                    logger.warning(f"解析字幕任务元数据失败 {blob.name}: {e}")
        logger.info(f"从GCS加载了 {count} 个字幕任务")
    except Exception as e:
        logger.warning(f"从GCS加载字幕任务失败: {e}")


def _save_subtitle_task_meta(task: SubtitleTask) -> None:
    """保存字幕任务元数据到 GCS"""
    try:
        upload_json(
            f"vigloo-subtitle-uploads/tasks/{task.task_id}.json",
            json.dumps(task.model_dump(), ensure_ascii=False, default=str),
            bucket_name=settings.subtitle_bucket,
        )
    except Exception as e:
        logger.warning(f"保存字幕任务元数据到GCS失败: {e}")


# 支持的语言
SUPPORTED_LANGUAGES = {
    "zh": "中文",
    "zh-TW": "繁体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
    "id": "Bahasa Indonesia",
    "ar": "العربية",
    "th": "ไทย",
    "vi": "Tiếng Việt",
    "fr": "Français",
    "de": "Deutsch",
    "pt": "Português",
    "ru": "Русский",
}


@router.get("/languages")
async def get_languages():
    """获取支持的语言列表"""
    return {
        "languages": [
            {"code": code, "name": name}
            for code, name in SUPPORTED_LANGUAGES.items()
        ]
    }


# ==================== 视频管理（与裂变模块一致） ====================


@router.get("/videos", summary="获取用户已上传的字幕视频列表")
def list_videos(
    max_results: int = Query(100, ge=1, le=500),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """列出用户的字幕视频（优先从 Firestore 元数据读取，同时扫描 GCS）"""
    from google.cloud import storage as gcs_storage
    from app.services.subtitle_video_metadata_service import SubtitleVideoMetadataService

    try:
        storage_client = gcs_storage.Client()
        bucket_name = settings.subtitle_bucket
        bucket = storage_client.bucket(bucket_name)

        # 从 Firestore 加载元数据
        metadata_map: Dict[str, dict] = {}
        metadata_service = SubtitleVideoMetadataService()
        metadata_videos = metadata_service.list_user_videos(current_user.user_id)
        for meta in metadata_videos:
            gcs_path = meta.get("gcs_path", "")
            if gcs_path:
                metadata_map[gcs_path] = meta

        # 扫描 GCS 桶中该用户的视频
        prefix = f"vigloo-subtitle-uploads/uploads/{current_user.user_id}/"
        videos = []
        video_exts = ('.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.webm', '.flv')

        for blob in bucket.list_blobs(prefix=prefix, max_results=max_results):
            if blob.name.lower().endswith(video_exts):
                gcs_path = f"gs://{bucket_name}/{blob.name}"
                meta = metadata_map.pop(gcs_path, {})

                updated_str = None
                updated_at = meta.get("updated_at") if meta else None
                if updated_at:
                    if hasattr(updated_at, '_seconds'):
                        updated_str = datetime.fromtimestamp(updated_at._seconds).isoformat()
                    elif hasattr(updated_at, 'isoformat'):
                        updated_str = updated_at.isoformat()
                elif blob.updated:
                    updated_str = blob.updated.isoformat()

                videos.append({
                    "video_id": meta.get("video_id", blob.name),
                    "name": blob.name.split('/')[-1],
                    "display_name": meta.get("display_name"),
                    "original_filename": meta.get("original_filename"),
                    "gcs_path": gcs_path,
                    "size": meta.get("file_size") or blob.size or 0,
                    "updated": updated_str,
                })

        # 补充 Firestore 中有但 GCS 扫描未覆盖的记录
        for gcs_path, meta in metadata_map.items():
            updated_at = meta.get("updated_at")
            updated_str = None
            if updated_at:
                if hasattr(updated_at, '_seconds'):
                    updated_str = datetime.fromtimestamp(updated_at._seconds).isoformat()
                elif hasattr(updated_at, 'isoformat'):
                    updated_str = updated_at.isoformat()
            videos.append({
                "video_id": meta.get("video_id", ""),
                "name": meta.get("gcs_blob_name", "").split('/')[-1],
                "display_name": meta.get("display_name"),
                "original_filename": meta.get("original_filename"),
                "gcs_path": gcs_path,
                "size": meta.get("file_size", 0),
                "updated": updated_str,
            })

        return {"videos": videos, "total": len(videos)}
    except Exception as e:
        logger.error(f"获取字幕视频列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取视频列表失败: {str(e)}",
        )


@router.post("/upload", summary="上传视频文件到GCS（仅上传，不创建任务）")
async def upload_video(
    file: UploadFile = File(...),
    display_name: Optional[str] = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """上传视频/音频文件到 GCS 并创建元数据（与裂变模块逻辑一致）"""
    from google.cloud import storage as gcs_storage
    from app.services.subtitle_video_metadata_service import SubtitleVideoMetadataService

    # 验证文件类型
    allowed_types = ("video/", "audio/")
    if file.content_type and not any(file.content_type.startswith(t) for t in allowed_types):
        # 兜底：按扩展名判断
        allowed_exts = ('.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.webm', '.flv', '.wmv')
        if not file.filename or not file.filename.lower().endswith(allowed_exts):
            raise HTTPException(status_code=400, detail="只支持视频或音频文件")

    try:
        # 生成唯一文件名
        file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "mp4"
        unique_filename = f"{uuid.uuid4()}.{file_ext}"

        # GCS 路径
        bucket_name = settings.subtitle_bucket
        blob_name = f"vigloo-subtitle-uploads/uploads/{current_user.user_id}/{unique_filename}"
        gcs_path = f"gs://{bucket_name}/{blob_name}"

        # 读取文件内容
        content = await file.read()

        # 上传到 GCS
        storage_client = gcs_storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        content_type = file.content_type or "video/mp4"
        blob.upload_from_string(content, content_type=content_type)

        # 确定显示名称
        if not display_name or not display_name.strip():
            display_name = file.filename.rsplit(".", 1)[0] if file.filename and "." in file.filename else file.filename or "unknown"

        # 创建 Firestore 元数据
        metadata_service = SubtitleVideoMetadataService()
        try:
            video_id = metadata_service.create_video_metadata(
                user_id=current_user.user_id,
                gcs_path=gcs_path,
                gcs_bucket=bucket_name,
                gcs_blob_name=blob_name,
                display_name=display_name.strip(),
                original_filename=file.filename or "unknown",
                file_size=len(content),
                content_type=content_type,
                file_extension=file_ext,
            )
        except Exception as e:
            blob.delete()
            raise HTTPException(status_code=500, detail=f"元数据创建失败: {str(e)}")

        return SubtitleVideoUploadResponse(
            video_id=video_id,
            filename=unique_filename,
            display_name=display_name.strip(),
            original_filename=file.filename or "unknown",
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


@router.post("/upload-url", summary="获取视频上传签名URL（支持大文件）")
def get_upload_url(
    payload: dict,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """生成视频上传的签名URL，客户端直传GCS，绕过 Cloud Run 请求体限制"""
    from google.cloud import storage as gcs_storage
    from app.services.subtitle_video_metadata_service import SubtitleVideoMetadataService
    import datetime as dt

    filename = payload.get("filename", "video.mp4")
    content_type = payload.get("content_type", "video/mp4")
    display_name = payload.get("display_name", "")
    file_size = payload.get("file_size", 0)

    # 生成唯一文件名
    file_ext = filename.split(".")[-1] if "." in filename else "mp4"
    unique_filename = f"{uuid.uuid4()}.{file_ext}"

    # GCS 路径
    bucket_name = settings.subtitle_bucket
    blob_name = f"vigloo-subtitle-uploads/uploads/{current_user.user_id}/{unique_filename}"
    gcs_path = f"gs://{bucket_name}/{blob_name}"

    try:
        storage_client = gcs_storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # 生成签名URL（有效期15分钟）
        upload_url = blob.generate_signed_url(
            version="v4",
            expiration=dt.timedelta(minutes=15),
            method="PUT",
            content_type=content_type,
        )

        # 预创建 Firestore 元数据
        if not display_name or not display_name.strip():
            display_name = filename.rsplit(".", 1)[0] if "." in filename else filename

        metadata_service = SubtitleVideoMetadataService()
        video_id = metadata_service.create_video_metadata(
            user_id=current_user.user_id,
            gcs_path=gcs_path,
            gcs_bucket=bucket_name,
            gcs_blob_name=blob_name,
            display_name=display_name.strip(),
            original_filename=filename,
            file_size=file_size,
            content_type=content_type,
            file_extension=file_ext,
        )

        return {
            "upload_url": upload_url,
            "gcs_path": gcs_path,
            "video_id": video_id,
            "filename": unique_filename,
            "display_name": display_name.strip(),
            "original_filename": filename,
            "expires_in": 900,
        }
    except Exception as e:
        logger.error(f"生成字幕上传签名URL失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成上传URL失败: {str(e)}",
        )


@router.patch("/videos/{video_id}", summary="重命名视频")
def rename_video(
    video_id: str,
    payload: SubtitleVideoRenameRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """更新视频显示名称"""
    from app.services.subtitle_video_metadata_service import SubtitleVideoMetadataService

    metadata_service = SubtitleVideoMetadataService()
    try:
        success = metadata_service.update_display_name(
            video_id=video_id,
            user_id=current_user.user_id,
            display_name=payload.display_name,
        )
        if not success:
            raise HTTPException(status_code=404, detail="视频不存在")
        return {"video_id": video_id, "display_name": payload.display_name, "message": "重命名成功"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")


# ==================== 字幕任务 ====================


@router.post("/tasks", response_model=SubtitleTaskResponse, summary="从已上传视频创建字幕任务")
async def create_task(
    request: SubtitleCreateTaskRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """从已上传的视频创建字幕生成任务（上传与任务创建分离）"""
    if not request.source_video_path.startswith("gs://"):
        raise HTTPException(status_code=400, detail="source_video_path 必须是 GCS 路径")

    task_id = str(uuid.uuid4())

    # 从 GCS 路径提取文件名
    filename = request.source_video_path.split("/")[-1]

    task = SubtitleTask(
        task_id=task_id,
        filename=filename,
        status=ProcessStatus.PENDING,
        source_language=request.source_language,
        target_languages=request.target_languages,
        created_by=current_user.user_id,
        created_at=datetime.now(),
    )
    tasks[task_id] = task
    _save_subtitle_task_meta(task)

    background_tasks.add_task(
        _process_subtitle_task, task_id, request.source_video_path,
        request.source_language, request.target_languages,
    )
    logger.info(f"字幕任务已创建: {task_id}, 文件: {request.source_video_path}")

    return SubtitleTaskResponse(
        task_id=task_id,
        message="任务已创建，正在处理中",
        status=ProcessStatus.PENDING,
    )


@router.get("/tasks", summary="获取当前用户的所有任务")
async def get_all_tasks(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """获取当前用户的所有任务"""
    import asyncio
    await asyncio.to_thread(_load_all_subtitle_tasks)
    user_tasks = [t for t in tasks.values() if t.created_by == current_user.user_id]
    return {"tasks": user_tasks, "total": len(user_tasks)}


@router.get("/task/{task_id}", response_model=SubtitleTaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """获取任务状态"""
    import asyncio
    await asyncio.to_thread(_load_all_subtitle_tasks)
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SubtitleTaskStatusResponse(task=tasks[task_id])


# ==================== 字幕处理 ====================


def _generate_srt_content(segments: list) -> str:
    """将字幕片段列表转换为 SRT 格式字符串"""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _seconds_to_srt_time(seg["start"])
        end = _seconds_to_srt_time(seg["end"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


def _generate_ass_content(segments: list, language: str) -> str:
    """将字幕片段列表转换为 ASS 格式字符串"""
    header = (
        "[Script Info]\n"
        f"Title: Subtitle - {language}\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,2,1,2,10,10,30,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    for seg in segments:
        start = _seconds_to_ass_time(seg["start"])
        end = _seconds_to_ass_time(seg["end"])
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{seg['text']}")
    return header + "\n".join(events) + "\n"


def _seconds_to_srt_time(seconds: float) -> str:
    """秒数转 SRT 时间格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _seconds_to_ass_time(seconds: float) -> str:
    """秒数转 ASS 时间格式 H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


async def _process_subtitle_task(
    task_id: str,
    gcs_path: str,
    source_language: Optional[str],
    target_languages: List[str],
) -> None:
    """后台处理字幕任务：下载音视频、转录、翻译、生成字幕文件。

    注意：当前使用占位字幕演示完整流程。
    接入实际转录引擎（Whisper / Google Speech-to-Text）后，
    只需替换下方 placeholder 段落即可。
    """
    try:
        tasks[task_id].status = ProcessStatus.PROCESSING
        tasks[task_id].progress = 10.0
        _save_subtitle_task_meta(tasks[task_id])

        # ------------------------------------------------------------------
        # 占位字幕内容（待接入 Whisper / Google Speech-to-Text 后替换）
        # ------------------------------------------------------------------
        import asyncio
        await asyncio.sleep(1)  # 模拟处理延迟

        placeholder_segments = [
            {"start": 0.0, "end": 3.0, "text": "[Placeholder] Audio transcription pending"},
            {"start": 3.0, "end": 6.0, "text": "[Placeholder] Connect Whisper or Google Speech API"},
            {"start": 6.0, "end": 9.0, "text": "[Placeholder] Subtitle will appear here"},
        ]

        tasks[task_id].progress = 50.0
        _save_subtitle_task_meta(tasks[task_id])

        # ------------------------------------------------------------------
        # 为每种目标语言生成 SRT + ASS 文件并上传到 GCS
        # ------------------------------------------------------------------
        bucket_name = settings.subtitle_bucket

        from app.schemas.subtitle import SubtitleFileInfo, SubtitleFormat

        subtitle_files: List[SubtitleFileInfo] = []

        for lang in target_languages:
            for fmt in ("srt", "ass"):
                if fmt == "srt":
                    content = _generate_srt_content(placeholder_segments)
                else:
                    content = _generate_ass_content(placeholder_segments, lang)

                blob_name = f"vigloo-subtitle-uploads/outputs/{task_id}/{lang}.{fmt}"
                content_bytes = content.encode("utf-8")
                content_type = "application/x-subrip" if fmt == "srt" else "text/x-ssa"
                upload_bytes(blob_name, content_bytes, content_type, bucket_name=bucket_name)

                subtitle_files.append(SubtitleFileInfo(
                    language=lang,
                    format=SubtitleFormat(fmt),
                    file_path=f"gs://{bucket_name}/{blob_name}",
                    file_size=len(content_bytes),
                ))

        tasks[task_id].subtitle_files = subtitle_files
        tasks[task_id].status = ProcessStatus.COMPLETED
        tasks[task_id].progress = 100.0
        tasks[task_id].completed_at = datetime.now()
        _save_subtitle_task_meta(tasks[task_id])
        logger.info(f"字幕任务完成: {task_id}, 生成 {len(subtitle_files)} 个文件")

    except Exception as e:
        logger.error(f"字幕任务处理失败: {task_id}, error: {e}")
        tasks[task_id].status = ProcessStatus.FAILED
        tasks[task_id].error_message = str(e)
        tasks[task_id].completed_at = datetime.now()
        _save_subtitle_task_meta(tasks[task_id])


@router.get("/download/{task_id}/{language}/{subtitle_format}")
async def download_subtitle(
    task_id: str,
    language: str,
    subtitle_format: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """获取字幕文件的签名下载链接（有效期1小时）"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    if task.status != ProcessStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成")

    if subtitle_format not in ("srt", "ass"):
        raise HTTPException(status_code=400, detail="不支持的字幕格式，仅支持 srt/ass")

    try:
        blob_name = f"vigloo-subtitle-uploads/outputs/{task_id}/{language}.{subtitle_format}"

        if not blob_exists(blob_name, bucket_name=settings.subtitle_bucket):
            raise HTTPException(status_code=404, detail="字幕文件不存在或尚未生成")

        download_filename = f"{task.filename}_{language}.{subtitle_format}"
        content_type = "application/x-subrip" if subtitle_format == "srt" else "text/x-ssa"

        download_url = generate_download_signed_url(
            blob_name=blob_name,
            download_filename=download_filename,
            content_type=content_type,
            bucket_name=settings.subtitle_bucket,
        )

        return {"download_url": download_url, "expires_in": 3600}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成字幕下载链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
