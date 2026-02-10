"""
字幕翻译和生成 API 端点
"""
import logging
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 任务存储（生产环境应使用数据库）
subtitle_tasks = {}


@router.get("/languages")
async def get_supported_languages():
    """获取支持的语言列表"""
    languages = {
        "zh": "简体中文",
        "zh-TW": "繁体中文",
        "en": "English",
        "ja": "日本語",
        "ko": "한국어",
        "es": "Español",
        "id": "Bahasa Indonesia",
        "ar": "العربية",
        "th": "ภาษาไทย",
        "vi": "Tiếng Việt",
        "fr": "Français",
    }
    return {
        "languages": [
            {"code": code, "name": name}
            for code, name in languages.items()
        ]
    }


@router.get("/config")
async def get_subtitle_config():
    """获取字幕系统配置"""
    return {
        "max_file_size": 500 * 1024 * 1024,  # 500MB
        "max_batch_files": 50,
        "supported_audio_formats": [".mp3", ".wav"],
        "supported_video_formats": [".mp4", ".mov"],
        "subtitle_formats": ["srt", "ass"],
        "whisper_model": "base",
    }


@router.post("/upload")
async def upload_audio_for_subtitle(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_language: Optional[str] = Form(None),
    target_languages: str = Form(...),
    subtitle_formats: str = Form("srt"),
    filter_filler_words: bool = Form(True),
    max_chars_per_line: int = Form(40),
):
    """
    上传音频/视频文件并生成多语言字幕
    """
    try:
        # 解析参数
        target_langs = json.loads(target_languages)
        formats = json.loads(subtitle_formats)
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建上传目录
        upload_dir = Path(settings.base_dir) / "uploads" / "subtitles"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存上传文件
        file_ext = Path(file.filename).suffix.lower()
        upload_path = upload_dir / f"{task_id}{file_ext}"
        
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"字幕任务文件上传成功: {file.filename} -> {upload_path}")
        
        # 创建任务记录
        subtitle_tasks[task_id] = {
            "task_id": task_id,
            "filename": file.filename,
            "status": "pending",
            "progress": 0.0,
            "source_language": source_language,
            "target_languages": target_langs,
            "subtitle_formats": formats,
            "created_at": datetime.now().isoformat(),
            "subtitle_files": []
        }
        
        # 后台处理（这里需要实现实际的处理逻辑）
        # background_tasks.add_task(process_subtitle_task, task_id, upload_path, ...)
        
        return {
            "task_id": task_id,
            "message": "字幕生成任务已创建",
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"字幕文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_subtitle_task_status(task_id: str):
    """获取字幕任务状态"""
    if task_id not in subtitle_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {"task": subtitle_tasks[task_id]}


@router.get("/tasks")
async def get_all_subtitle_tasks():
    """获取所有字幕任务"""
    return {
        "tasks": list(subtitle_tasks.values()),
        "total": len(subtitle_tasks)
    }


@router.get("/download/{task_id}/{language}/{format}")
async def download_subtitle_file(task_id: str, language: str, format: str):
    """下载生成的字幕文件"""
    if task_id not in subtitle_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = subtitle_tasks[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    # 查找字幕文件
    output_dir = Path(settings.base_dir) / "outputs" / "subtitles"
    file_path = output_dir / f"{task_id}_{language}.{format}"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="字幕文件不存在")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream"
    )

