"""字幕生成 API 路由

所有上传的音视频文件和生成的字幕都存储在 GCS 存储桶中：
  桶名: vigloo-fission-uploads (由 settings.subtitle_bucket 配置)
  路径: vigloo-subtitle-uploads/uploads/{user_id}/{task_id}.mp4  (上传的音视频)
        vigloo-subtitle-uploads/tasks/{task_id}.json              (任务元数据)
        vigloo-subtitle-uploads/outputs/{task_id}/{lang}.srt      (生成的字幕)
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.api.deps import get_current_user, AuthenticatedUser
from fastapi import Depends

from app.schemas.subtitle import (
    LanguageCode,
    SubtitleFormat,
    ProcessStatus,
    SubtitleTask,
    SubtitleTaskResponse,
    SubtitleTaskStatusResponse,
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


@router.get("/tasks")
async def get_all_tasks(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """获取当前用户的所有任务"""
    _load_all_subtitle_tasks()
    user_tasks = [t for t in tasks.values()]
    return {"tasks": user_tasks, "total": len(user_tasks)}


@router.get("/task/{task_id}", response_model=SubtitleTaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """获取任务状态"""
    _load_all_subtitle_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SubtitleTaskStatusResponse(task=tasks[task_id])


@router.post("/upload", response_model=SubtitleTaskResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_languages: str = Form(...),
    source_language: Optional[str] = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """上传音视频文件并创建字幕生成任务（文件存储到GCS）"""
    try:
        target_langs = json.loads(target_languages)
    except json.JSONDecodeError:
        target_langs = [target_languages]

    task_id = str(uuid.uuid4())

    # 读取文件内容
    content = await file.read()

    # 上传到GCS
    try:
        from pathlib import Path as _Path
        file_ext = _Path(file.filename).suffix.lower() if file.filename else ".mp4"
        blob_name = f"vigloo-subtitle-uploads/uploads/{current_user.user_id}/{task_id}{file_ext}"
        bucket_name = settings.subtitle_bucket
        gcs_path = f"gs://{bucket_name}/{blob_name}"
        upload_bytes(blob_name, content, file.content_type or "video/mp4", bucket_name=bucket_name)

        logger.info(f"字幕文件已上传到GCS: {gcs_path}")
    except Exception as e:
        logger.error(f"上传文件到GCS失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")

    task = SubtitleTask(
        task_id=task_id,
        filename=file.filename or "unknown",
        status=ProcessStatus.PENDING,
        source_language=source_language,
        target_languages=target_langs,
        created_at=datetime.now(),
    )
    tasks[task_id] = task
    _save_subtitle_task_meta(task)  # 持久化到 GCS

    # 后台处理字幕任务
    background_tasks.add_task(
        _process_subtitle_task, task_id, gcs_path, source_language, target_langs
    )
    logger.info(f"字幕任务已创建: {task_id}, 文件: {gcs_path}")

    return SubtitleTaskResponse(
        task_id=task_id,
        message="任务已创建，正在处理中",
        status=ProcessStatus.PENDING,
    )


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
                upload_bytes(blob_name, content_bytes, content_type)

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
    """获取字幕文件的签名下载链接（有效期1小时，与裂变模块一致）"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    if task.status != ProcessStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成")

    # 验证格式
    if subtitle_format not in ("srt", "ass"):
        raise HTTPException(status_code=400, detail="不支持的字幕格式，仅支持 srt/ass")

    try:
        blob_name = f"vigloo-subtitle-uploads/outputs/{task_id}/{language}.{subtitle_format}"

        if not blob_exists(blob_name):
            raise HTTPException(status_code=404, detail="字幕文件不存在或尚未生成")

        download_filename = f"{task.filename}_{language}.{subtitle_format}"
        content_type = "application/x-subrip" if subtitle_format == "srt" else "text/x-ssa"

        download_url = generate_download_signed_url(
            blob_name=blob_name,
            download_filename=download_filename,
            content_type=content_type,
        )

        return {"download_url": download_url, "expires_in": 3600}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成字幕下载链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
