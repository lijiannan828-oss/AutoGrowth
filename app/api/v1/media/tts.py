"""
文本转语音 (TTS) API 端点
"""
import logging
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 任务存储（生产环境应使用数据库）
tts_tasks = {}


@router.get("/voices")
async def get_available_voices():
    """获取可用的语音列表"""
    voices = {
        "zh": [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 (女)", "gender": "female"},
            {"id": "zh-CN-YunxiNeural", "name": "云希 (男)", "gender": "male"},
            {"id": "zh-CN-YunyangNeural", "name": "云扬 (男)", "gender": "male"},
        ],
        "en": [
            {"id": "en-US-JennyNeural", "name": "Jenny (Female)", "gender": "female"},
            {"id": "en-US-GuyNeural", "name": "Guy (Male)", "gender": "male"},
        ],
        "ja": [
            {"id": "ja-JP-NanamiNeural", "name": "七海 (女)", "gender": "female"},
            {"id": "ja-JP-KeitaNeural", "name": "圭太 (男)", "gender": "male"},
        ],
    }
    return {"voices": voices}


@router.get("/config")
async def get_tts_config():
    """获取TTS系统配置"""
    return {
        "max_text_length": 10000,
        "max_batch_texts": 100,
        "supported_formats": ["mp3", "wav"],
        "default_voice": "zh-CN-XiaoxiaoNeural",
        "default_speed": 1.0,
        "default_pitch": 0,
    }


@router.post("/synthesize")
async def synthesize_speech(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    language: str = Form("zh"),
    voice_id: str = Form("zh-CN-XiaoxiaoNeural"),
    speed: float = Form(1.0),
    pitch: int = Form(0),
    output_format: str = Form("mp3"),
):
    """
    将文本转换为语音
    """
    try:
        # 验证参数
        if len(text) > 10000:
            raise HTTPException(status_code=400, detail="文本长度超过限制")
        
        if speed < 0.5 or speed > 2.0:
            raise HTTPException(status_code=400, detail="语速必须在0.5-2.0之间")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建输出目录
        output_dir = Path(settings.base_dir) / "outputs" / "tts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"TTS任务创建: {task_id}, 文本长度: {len(text)}")
        
        # 创建任务记录
        tts_tasks[task_id] = {
            "task_id": task_id,
            "text": text[:100] + "..." if len(text) > 100 else text,
            "status": "pending",
            "progress": 0.0,
            "language": language,
            "voice_id": voice_id,
            "speed": speed,
            "pitch": pitch,
            "output_format": output_format,
            "created_at": datetime.now().isoformat(),
            "audio_file": None
        }
        
        # 后台处理（这里需要实现实际的TTS处理逻辑）
        # background_tasks.add_task(process_tts_task, task_id, text, ...)
        
        return {
            "task_id": task_id,
            "message": "TTS任务已创建",
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"TTS任务创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-synthesize")
async def batch_synthesize_speech(
    background_tasks: BackgroundTasks,
    texts: str = Form(...),
    language: str = Form("zh"),
    voice_id: str = Form("zh-CN-XiaoxiaoNeural"),
    speed: float = Form(1.0),
    pitch: int = Form(0),
    output_format: str = Form("mp3"),
):
    """
    批量将文本转换为语音
    """
    try:
        # 解析文本列表
        text_list = json.loads(texts)
        
        if len(text_list) > 100:
            raise HTTPException(status_code=400, detail="批量文本数量超过限制")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        logger.info(f"批量TTS任务创建: {task_id}, 文本数量: {len(text_list)}")
        
        # 创建任务记录
        tts_tasks[task_id] = {
            "task_id": task_id,
            "batch_count": len(text_list),
            "status": "pending",
            "progress": 0.0,
            "language": language,
            "voice_id": voice_id,
            "speed": speed,
            "pitch": pitch,
            "output_format": output_format,
            "created_at": datetime.now().isoformat(),
            "audio_files": []
        }
        
        return {
            "task_id": task_id,
            "message": "批量TTS任务已创建",
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"批量TTS任务创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_tts_task_status(task_id: str):
    """获取TTS任务状态"""
    if task_id not in tts_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {"task": tts_tasks[task_id]}


@router.get("/tasks")
async def get_all_tts_tasks():
    """获取所有TTS任务"""
    return {
        "tasks": list(tts_tasks.values()),
        "total": len(tts_tasks)
    }


@router.get("/download/{task_id}")
async def download_tts_audio(task_id: str):
    """下载生成的音频文件"""
    if task_id not in tts_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tts_tasks[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    # 查找音频文件
    output_dir = Path(settings.base_dir) / "outputs" / "tts"
    file_path = output_dir / f"{task_id}.{task['output_format']}"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="音频文件不存在")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream"
    )

