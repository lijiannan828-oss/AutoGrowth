"""
文本转语音 (TTS) API 端点
基于 Microsoft Edge TTS

所有上传和生成的音频文件都存储在 GCS 存储桶中：
  桶名: vigloo-fission-uploads (由 settings.tts_bucket 配置)
  路径: vigloo-tts-uploads/source/{task_id}/xxx.txt   (批量上传的源文件)
        vigloo-tts-uploads/outputs/{task_id}.mp3      (生成的音频)
        vigloo-tts-uploads/tasks/{task_id}.json       (任务元数据)
"""
import asyncio
import io
import json
import logging
import re
import uuid
import zipfile
from xml.etree import ElementTree
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import APIRouter, Form, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel

from app.core.config import settings
from app.utils.gcs import (
    get_bucket,
    upload_bytes,
    upload_json,
    generate_download_signed_url,
    blob_exists,
    get_default_bucket_name,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Pydantic 模型 ----

class RoleVoiceConfig(BaseModel):
    """单个角色的语音配置"""
    voice_id: str
    rate: float = 1.0
    pitch: str = "+0Hz"
    volume: str = "+0%"


class DialogueRequest(BaseModel):
    """多角色对话转语音请求"""
    text: str
    role_voices: Dict[str, RoleVoiceConfig]
    silence_gap: int = 500  # 句间静音毫秒
    output_format: str = "mp3"
    filename: Optional[str] = None


class DialogueSegment(BaseModel):
    """解析后的对话片段"""
    role: str
    text: str


def _extract_docx_text(content: bytes) -> str:
    """从 .docx 文件提取纯文本（全选复制逻辑）"""
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        xml_content = zf.read("word/document.xml")
    tree = ElementTree.fromstring(xml_content)
    paragraphs = []
    for p in tree.iter(f"{ns}p"):
        texts = [t.text for t in p.iter(f"{ns}t") if t.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


# ---- 对话文本解析 ----

def _parse_dialogue_text(text: str) -> List[Dict[str, str]]:
    """
    解析多角色对话文本，支持格式：
      角色名: 对话内容
      角色名：对话内容
    没有角色前缀的行视为"旁白"
    """
    segments: List[Dict[str, str]] = []
    pattern = re.compile(r"^(.{1,20})[：:]\s*(.+)$")

    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            segments.append({"role": m.group(1).strip(), "text": m.group(2).strip()})
        else:
            segments.append({"role": "旁白", "text": line})

    return segments

# 任务存储（同时持久化到GCS）
tts_tasks = {}
_tts_loaded_from_gcs = False


def _load_all_tts_tasks() -> None:
    """从 GCS 加载所有 TTS 任务元数据到内存"""
    global _tts_loaded_from_gcs
    if _tts_loaded_from_gcs:
        return
    _tts_loaded_from_gcs = True
    try:
        bucket, _ = get_bucket(settings.tts_bucket)
        blobs = bucket.list_blobs(prefix="vigloo-tts-uploads/tasks/")
        count = 0
        for blob in blobs:
            if blob.name.endswith(".json"):
                try:
                    data = json.loads(blob.download_as_text())
                    tid = data.get("task_id")
                    if tid and tid not in tts_tasks:
                        tts_tasks[tid] = data
                        count += 1
                except Exception as e:
                    logger.warning(f"解析TTS任务元数据失败 {blob.name}: {e}")
        logger.info(f"从GCS加载了 {count} 个TTS任务")
    except Exception as e:
        logger.warning(f"从GCS加载TTS任务失败: {e}")


def _save_tts_task_meta(task: dict) -> None:
    """保存 TTS 任务元数据到 GCS"""
    try:
        upload_json(
            f"vigloo-tts-uploads/tasks/{task['task_id']}.json",
            json.dumps(task, ensure_ascii=False, default=str),
            bucket_name=settings.tts_bucket,
        )
    except Exception as e:
        logger.warning(f"保存TTS任务元数据到GCS失败: {e}")


async def _process_tts_task(
    task_id: str,
    text: str,
    voice_id: str,
    rate: float,
    pitch: str,
    volume: str,
    output_format: str,
) -> None:
    """后台处理 TTS 任务：调用 edge-tts 生成音频并上传到 GCS"""
    try:
        import edge_tts

        tts_tasks[task_id]["status"] = "processing"
        tts_tasks[task_id]["progress"] = 10.0
        _save_tts_task_meta(tts_tasks[task_id])

        # 构建 edge-tts 语速参数
        rate_str = f"+{int((rate - 1) * 100)}%" if rate >= 1 else f"{int((rate - 1) * 100)}%"

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=rate_str,
            pitch=pitch,
            volume=volume,
        )

        # 收集音频数据
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        tts_tasks[task_id]["progress"] = 70.0
        _save_tts_task_meta(tts_tasks[task_id])

        # 上传到 GCS
        bucket_name = settings.tts_bucket
        blob_name = f"vigloo-tts-uploads/outputs/{task_id}.{output_format}"
        content_type = "audio/mpeg" if output_format == "mp3" else "audio/wav"
        upload_bytes(blob_name, bytes(audio_data), content_type, bucket_name=bucket_name)

        tts_tasks[task_id]["status"] = "completed"
        tts_tasks[task_id]["progress"] = 100.0
        tts_tasks[task_id]["gcs_path"] = f"gs://{bucket_name}/{blob_name}"
        tts_tasks[task_id]["audio_file"] = task_id  # 前端通过此字段判断是否可下载
        _save_tts_task_meta(tts_tasks[task_id])
        logger.info(f"TTS任务完成: {task_id}")

    except Exception as e:
        logger.error(f"TTS后台处理失败: {task_id}, error: {e}")
        tts_tasks[task_id]["status"] = "failed"
        tts_tasks[task_id]["error_message"] = str(e)
        _save_tts_task_meta(tts_tasks[task_id])


# 完整的音色列表
VOICES_DATA = {
    "zh": [
        {"voice_id": "zh-CN-XiaoxiaoNeural", "name": "晓晓（女声-温柔）", "language": "zh", "gender": "female"},
        {"voice_id": "zh-CN-YunxiNeural", "name": "云希（男声-阳光）", "language": "zh", "gender": "male"},
        {"voice_id": "zh-CN-YunyangNeural", "name": "云扬（男声-成熟）", "language": "zh", "gender": "male"},
        {"voice_id": "zh-CN-XiaoyiNeural", "name": "晓伊（女声-知性）", "language": "zh", "gender": "female"},
        {"voice_id": "zh-CN-YunjianNeural", "name": "云健（男声-磁性）", "language": "zh", "gender": "male"},
        {"voice_id": "zh-CN-XiaochenNeural", "name": "晓辰（女声-活泼）", "language": "zh", "gender": "female"},
    ],
    "zh-TW": [
        {"voice_id": "zh-TW-HsiaoChenNeural", "name": "曉臻（女声）", "language": "zh-TW", "gender": "female"},
        {"voice_id": "zh-TW-YunJheNeural", "name": "雲哲（男声）", "language": "zh-TW", "gender": "male"},
        {"voice_id": "zh-TW-HsiaoYuNeural", "name": "曉雨（女声）", "language": "zh-TW", "gender": "female"},
    ],
    "en": [
        {"voice_id": "en-US-JennyNeural", "name": "Jenny（女声-友好）", "language": "en", "gender": "female"},
        {"voice_id": "en-US-GuyNeural", "name": "Guy（男声-专业）", "language": "en", "gender": "male"},
        {"voice_id": "en-US-AriaNeural", "name": "Aria（女声-自然）", "language": "en", "gender": "female"},
        {"voice_id": "en-US-DavisNeural", "name": "Davis（男声-温暖）", "language": "en", "gender": "male"},
        {"voice_id": "en-US-AmberNeural", "name": "Amber（女声-活力）", "language": "en", "gender": "female"},
    ],
    "ja": [
        {"voice_id": "ja-JP-NanamiNeural", "name": "七海（女声）", "language": "ja", "gender": "female"},
        {"voice_id": "ja-JP-KeitaNeural", "name": "圭太（男声）", "language": "ja", "gender": "male"},
        {"voice_id": "ja-JP-AoiNeural", "name": "葵（女声）", "language": "ja", "gender": "female"},
    ],
    "ko": [
        {"voice_id": "ko-KR-SunHiNeural", "name": "선희（女声）", "language": "ko", "gender": "female"},
        {"voice_id": "ko-KR-InJoonNeural", "name": "인준（男声）", "language": "ko", "gender": "male"},
        {"voice_id": "ko-KR-BongJinNeural", "name": "봉진（男声）", "language": "ko", "gender": "male"},
    ],
    "es": [
        {"voice_id": "es-ES-ElviraNeural", "name": "Elvira（女声）", "language": "es", "gender": "female"},
        {"voice_id": "es-ES-AlvaroNeural", "name": "Alvaro（男声）", "language": "es", "gender": "male"},
        {"voice_id": "es-MX-DaliaNeural", "name": "Dalia（女声-墨西哥）", "language": "es", "gender": "female"},
    ],
    "id": [
        {"voice_id": "id-ID-GadisNeural", "name": "Gadis（女声）", "language": "id", "gender": "female"},
        {"voice_id": "id-ID-ArdiNeural", "name": "Ardi（男声）", "language": "id", "gender": "male"},
    ],
    "ar": [
        {"voice_id": "ar-SA-ZariyahNeural", "name": "Zariyah（女声）", "language": "ar", "gender": "female"},
        {"voice_id": "ar-SA-HamedNeural", "name": "Hamed（男声）", "language": "ar", "gender": "male"},
    ],
    "th": [
        {"voice_id": "th-TH-PremwadeeNeural", "name": "Premwadee（女声）", "language": "th", "gender": "female"},
        {"voice_id": "th-TH-NiwatNeural", "name": "Niwat（男声）", "language": "th", "gender": "male"},
    ],
    "vi": [
        {"voice_id": "vi-VN-HoaiMyNeural", "name": "Hoai My（女声）", "language": "vi", "gender": "female"},
        {"voice_id": "vi-VN-NamMinhNeural", "name": "Nam Minh（男声）", "language": "vi", "gender": "male"},
    ],
    "fr": [
        {"voice_id": "fr-FR-DeniseNeural", "name": "Denise（女声）", "language": "fr", "gender": "female"},
        {"voice_id": "fr-FR-HenriNeural", "name": "Henri（男声）", "language": "fr", "gender": "male"},
        {"voice_id": "fr-FR-BrigitteNeural", "name": "Brigitte（女声）", "language": "fr", "gender": "female"},
    ],
}


@router.get("/voices")
async def get_available_voices(language: Optional[str] = None):
    """获取可用的语音列表"""
    if language:
        voices = VOICES_DATA.get(language, [])
    else:
        # 返回所有音色
        voices = []
        for lang_voices in VOICES_DATA.values():
            voices.extend(lang_voices)
    
    return {"voices": voices}


@router.post("/convert")
async def convert_text_to_speech(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    voice_id: str = Form(...),
    rate: float = Form(1.0),
    pitch: str = Form("+0Hz"),
    volume: str = Form("+0%"),
    output_format: str = Form("mp3"),
    filename: Optional[str] = Form(None),
):
    """
    单个文本转语音
    """
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())

        logger.info(f"TTS任务创建: {task_id}, 文本长度: {len(text)}")

        # GCS 输出路径
        bucket_name = settings.tts_bucket
        gcs_output_path = f"gs://{bucket_name}/vigloo-tts-uploads/outputs/{task_id}.{output_format}"

        # 创建任务记录
        tts_tasks[task_id] = {
            "task_id": task_id,
            "text": text[:100] + "..." if len(text) > 100 else text,
            "status": "pending",
            "progress": 0.0,
            "voice_id": voice_id,
            "rate": rate,
            "pitch": pitch,
            "volume": volume,
            "output_format": output_format,
            "created_at": datetime.now().isoformat(),
            "audio_file": None,
            "gcs_path": gcs_output_path,
        }
        _save_tts_task_meta(tts_tasks[task_id])

        # 后台处理TTS任务
        background_tasks.add_task(
            _process_tts_task, task_id, text, voice_id, rate, pitch, volume, output_format
        )

        return {
            "task_id": task_id,
            "message": "TTS 任务已创建",
            "status": "pending"
        }

    except Exception as e:
        logger.error(f"TTS任务创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_convert_text_to_speech(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    voice_id: str = Form(...),
    rate: float = Form(1.0),
    output_format: str = Form("mp3"),
):
    """
    批量文本转语音（上传 .txt 文件，存储到GCS）
    """
    try:
        # 验证文件类型
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="只支持 .txt 文件")

        # 读取文件内容
        content = await file.read()
        text = content.decode('utf-8')

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 上传源文件到GCS
        try:
            bucket_name = settings.tts_bucket
            blob_name = f"vigloo-tts-uploads/source/{task_id}/{file.filename}"
            gcs_path = f"gs://{bucket_name}/{blob_name}"
            upload_bytes(blob_name, content, "text/plain", bucket_name=bucket_name)

            logger.info(f"TTS源文件已上传到GCS: {gcs_path}")
        except Exception as e:
            logger.warning(f"上传源文件到GCS失败（继续处理）: {str(e)}")
            gcs_path = None

        logger.info(f"批量TTS任务创建: {task_id}, 文件: {file.filename}")

        # 创建任务记录
        tts_tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0.0,
            "voice_id": voice_id,
            "rate": rate,
            "output_format": output_format,
            "created_at": datetime.now().isoformat(),
            "audio_file": None,
            "filename": file.filename,
            "gcs_source_path": gcs_path,
            "gcs_output_path": f"gs://{settings.tts_bucket}/vigloo-tts-uploads/outputs/{task_id}.{output_format}" if gcs_path else None,
        }
        _save_tts_task_meta(tts_tasks[task_id])

        # 后台处理批量TTS任务
        background_tasks.add_task(
            _process_tts_task, task_id, text, voice_id, rate, "+0Hz", "+0%", output_format
        )

        return {
            "task_id": task_id,
            "message": "批量 TTS 任务已创建",
            "status": "processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量TTS任务创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_tts_task_status(task_id: str):
    """获取TTS任务状态"""
    _load_all_tts_tasks()
    if task_id not in tts_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {"task": tts_tasks[task_id]}


@router.get("/tasks")
async def get_all_tts_tasks():
    """获取所有TTS任务"""
    _load_all_tts_tasks()
    tasks_list = sorted(
        tts_tasks.values(),
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )
    return {
        "tasks": tasks_list,
        "total": len(tasks_list)
    }


@router.get("/download/{task_id}")
async def download_tts_audio(task_id: str):
    """获取生成音频的签名下载链接（有效期1小时，与裂变模块一致）"""
    _load_all_tts_tasks()
    try:
        task = tts_tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.get("status") != "completed":
            raise HTTPException(status_code=400, detail="任务尚未完成")

        output_format = task.get("output_format", "mp3")
        blob_name = f"vigloo-tts-uploads/outputs/{task_id}.{output_format}"

        if not blob_exists(blob_name, bucket_name=settings.tts_bucket):
            raise HTTPException(status_code=404, detail="音频文件不存在或尚未生成")

        # 生成文件名
        display_name = task.get("filename") or task.get("text", task_id)
        # 截断过长的名称
        if len(display_name) > 50:
            display_name = display_name[:50]
        download_filename = f"{display_name}.{output_format}"
        media_type = "audio/mpeg" if output_format == "mp3" else "audio/wav"

        download_url = generate_download_signed_url(
            blob_name=blob_name,
            download_filename=download_filename,
            content_type=media_type,
            bucket_name=settings.tts_bucket,
        )

        return {"download_url": download_url, "expires_in": 3600}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成音频下载链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== 多角色对话 TTS =====================


@router.post("/dialogue/parse")
async def parse_dialogue_text(
    text: str = Form(None),
    file_id: str = Form(None),
    gcs_path: str = Form(None),
):
    """解析对话文本，返回检测到的角色列表和分段结果。支持直接文本、file_id、gcs_path"""
    actual_text = ""

    if text and text.strip():
        actual_text = text.strip()
    elif file_id:
        _load_all_tts_files()
        meta = _tts_files.get(file_id)
        if not meta:
            raise HTTPException(status_code=404, detail="源文件不存在")
        try:
            blob_name = meta["gcs_blob_name"]
            bucket, _ = get_bucket(settings.tts_bucket)
            blob = bucket.blob(blob_name)
            content = blob.download_as_bytes()
            ext = meta.get("file_extension", ".txt").lower()
            if ext == ".txt":
                actual_text = content.decode("utf-8")
            elif ext == ".docx":
                try:
                    actual_text = _extract_docx_text(content)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f".docx 文件解析失败: {str(e)}")
            elif ext == ".doc":
                raise HTTPException(status_code=400, detail="不支持旧版 .doc 格式，请转换为 .docx 后重试")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取源文件失败: {str(e)}")
    elif gcs_path:
        try:
            path = gcs_path.replace("gs://", "")
            bucket_name_part = path.split("/", 1)[0]
            blob_name = path.split("/", 1)[1] if "/" in path else ""
            bucket, _ = get_bucket(bucket_name_part)
            blob = bucket.blob(blob_name)
            content = blob.download_as_bytes()
            actual_text = content.decode("utf-8")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取GCS文件失败: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="请提供文本内容、源文件ID或GCS路径")

    if not actual_text.strip():
        raise HTTPException(status_code=400, detail="文本内容为空")

    segments = _parse_dialogue_text(actual_text)
    roles = list(dict.fromkeys(seg["role"] for seg in segments))
    return {"roles": roles, "segments": segments, "text": actual_text}


async def _generate_segment_audio(
    text: str, voice_id: str, rate: float, pitch: str, volume: str
) -> bytes:
    """用 edge-tts 为单段文本生成音频，返回 mp3 bytes"""
    import edge_tts

    rate_str = f"+{int((rate - 1) * 100)}%" if rate >= 1 else f"{int((rate - 1) * 100)}%"
    communicate = edge_tts.Communicate(
        text=text, voice=voice_id, rate=rate_str, pitch=pitch, volume=volume,
    )
    audio_data = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.extend(chunk["data"])
    return bytes(audio_data)


async def _process_dialogue_task(
    task_id: str,
    segments: List[Dict[str, str]],
    role_voices: Dict[str, Dict],
    silence_gap: int,
    output_format: str,
) -> None:
    """后台处理多角色对话 TTS 任务"""
    try:
        from pydub import AudioSegment

        tts_tasks[task_id]["status"] = "processing"
        tts_tasks[task_id]["progress"] = 5.0
        _save_tts_task_meta(tts_tasks[task_id])

        # 生成静音片段
        silence = AudioSegment.silent(duration=silence_gap)
        combined = AudioSegment.empty()
        total = len(segments)

        for idx, seg in enumerate(segments):
            role = seg["role"]
            cfg = role_voices.get(role, {})
            voice_id = cfg.get("voice_id", "zh-CN-XiaoxiaoNeural")
            rate = cfg.get("rate", 1.0)
            pitch = cfg.get("pitch", "+0Hz")
            volume = cfg.get("volume", "+0%")

            audio_bytes = await _generate_segment_audio(
                seg["text"], voice_id, rate, pitch, volume
            )
            seg_audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            combined += seg_audio
            if idx < total - 1:
                combined += silence

            progress = 5.0 + (idx + 1) / total * 75.0
            tts_tasks[task_id]["progress"] = round(progress, 1)
            _save_tts_task_meta(tts_tasks[task_id])

        # 导出并上传
        buf = io.BytesIO()
        export_fmt = "mp3" if output_format == "mp3" else "wav"
        combined.export(buf, format=export_fmt)
        buf.seek(0)

        bucket_name = settings.tts_bucket
        blob_name = f"vigloo-tts-uploads/outputs/{task_id}.{output_format}"
        content_type = "audio/mpeg" if output_format == "mp3" else "audio/wav"
        upload_bytes(blob_name, buf.read(), content_type, bucket_name=bucket_name)

        tts_tasks[task_id]["status"] = "completed"
        tts_tasks[task_id]["progress"] = 100.0
        tts_tasks[task_id]["gcs_path"] = f"gs://{bucket_name}/{blob_name}"
        tts_tasks[task_id]["audio_file"] = task_id
        _save_tts_task_meta(tts_tasks[task_id])
        logger.info(f"多角色对话TTS任务完成: {task_id}")

    except Exception as e:
        logger.error(f"多角色对话TTS处理失败: {task_id}, error: {e}")
        tts_tasks[task_id]["status"] = "failed"
        tts_tasks[task_id]["error_message"] = str(e)
        _save_tts_task_meta(tts_tasks[task_id])


@router.post("/dialogue")
async def convert_dialogue_to_speech(
    req: DialogueRequest,
    background_tasks: BackgroundTasks,
):
    """多角色对话转语音：按角色拆分文本，分别生成音频后拼接"""
    segments = _parse_dialogue_text(req.text)
    if not segments:
        raise HTTPException(status_code=400, detail="未解析到有效对话内容")

    # 检查每个角色是否都配置了音色
    roles_in_text = set(seg["role"] for seg in segments)
    missing = roles_in_text - set(req.role_voices.keys())
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"以下角色未配置音色: {', '.join(missing)}",
        )

    task_id = str(uuid.uuid4())
    bucket_name = settings.tts_bucket

    tts_tasks[task_id] = {
        "task_id": task_id,
        "text": req.text[:100] + "..." if len(req.text) > 100 else req.text,
        "type": "dialogue",
        "status": "pending",
        "progress": 0.0,
        "roles": list(roles_in_text),
        "segment_count": len(segments),
        "silence_gap": req.silence_gap,
        "output_format": req.output_format,
        "created_at": datetime.now().isoformat(),
        "audio_file": None,
        "filename": req.filename,
        "gcs_path": f"gs://{bucket_name}/vigloo-tts-uploads/outputs/"
                    f"{task_id}.{req.output_format}",
    }
    _save_tts_task_meta(tts_tasks[task_id])

    role_voices_dict = {
        k: v.model_dump() for k, v in req.role_voices.items()
    }
    background_tasks.add_task(
        _process_dialogue_task,
        task_id, segments, role_voices_dict,
        req.silence_gap, req.output_format,
    )

    return {
        "task_id": task_id,
        "message": "多角色对话 TTS 任务已创建",
        "status": "pending",
        "segment_count": len(segments),
        "roles": list(roles_in_text),
    }


# ===================== TTS 源文件管理 =====================

# 源文件元数据缓存
_tts_files: Dict[str, dict] = {}
_tts_files_loaded = False

_SUPPORTED_EXTENSIONS = {".txt", ".doc", ".docx"}


def _load_all_tts_files() -> None:
    """从 GCS 加载所有 TTS 源文件元数据"""
    global _tts_files_loaded
    if _tts_files_loaded:
        return
    _tts_files_loaded = True
    try:
        bucket, _ = get_bucket(settings.tts_bucket)
        blobs = bucket.list_blobs(prefix="vigloo-tts-uploads/files/meta/")
        count = 0
        for blob in blobs:
            if blob.name.endswith(".json"):
                try:
                    data = json.loads(blob.download_as_text())
                    fid = data.get("file_id")
                    if fid and fid not in _tts_files:
                        _tts_files[fid] = data
                        count += 1
                except Exception as e:
                    logger.warning(f"解析TTS文件元数据失败 {blob.name}: {e}")
        logger.info(f"从GCS加载了 {count} 个TTS源文件元数据")
    except Exception as e:
        logger.warning(f"从GCS加载TTS源文件元数据失败: {e}")


def _save_tts_file_meta(meta: dict) -> None:
    """保存 TTS 源文件元数据到 GCS"""
    try:
        upload_json(
            f"vigloo-tts-uploads/files/meta/{meta['file_id']}.json",
            json.dumps(meta, ensure_ascii=False, default=str),
            bucket_name=settings.tts_bucket,
        )
    except Exception as e:
        logger.warning(f"保存TTS文件元数据到GCS失败: {e}")


@router.post("/upload")
async def upload_tts_source_file(
    file: UploadFile = File(...),
    display_name: Optional[str] = Form(None),
):
    """上传 TTS 源文件（.txt/.doc/.docx）到 GCS"""
    import os

    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 {ext}，仅支持 .txt / .doc / .docx",
        )

    try:
        content = await file.read()
        file_id = str(uuid.uuid4())
        bucket_name = settings.tts_bucket
        blob_name = f"vigloo-tts-uploads/files/source/{file_id}/{file.filename}"
        gcs_path = f"gs://{bucket_name}/{blob_name}"

        # 上传文件到 GCS
        content_type = file.content_type or "application/octet-stream"
        upload_bytes(blob_name, content, content_type, bucket_name=bucket_name)

        # 确定显示名称
        if not display_name or not display_name.strip():
            display_name = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename

        # 保存元数据
        meta = {
            "file_id": file_id,
            "display_name": display_name.strip(),
            "original_filename": file.filename,
            "gcs_path": gcs_path,
            "gcs_blob_name": blob_name,
            "file_size": len(content),
            "file_extension": ext,
            "content_type": content_type,
            "uploaded_at": datetime.now().isoformat(),
        }
        _tts_files[file_id] = meta
        _save_tts_file_meta(meta)

        logger.info(f"TTS源文件上传成功: {file_id} -> {gcs_path}")

        return {
            "file_id": file_id,
            "filename": file.filename,
            "display_name": display_name.strip(),
            "original_filename": file.filename,
            "gcs_path": gcs_path,
            "size": len(content),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS源文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/files")
async def list_tts_source_files():
    """列出所有已上传的 TTS 源文件"""
    _load_all_tts_files()
    files_list = sorted(
        _tts_files.values(),
        key=lambda x: x.get("uploaded_at", ""),
        reverse=True,
    )
    return {"files": files_list, "total": len(files_list)}


@router.post("/batch-upload")
async def batch_upload_tts_source_files(
    files: List[UploadFile] = File(...),
):
    """批量上传 TTS 源文件（.txt/.doc/.docx）到 GCS"""
    import os

    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")

    if len(files) > 20:
        raise HTTPException(status_code=400, detail="单次最多上传 20 个文件")

    results = []
    for file in files:
        if not file.filename:
            results.append({"filename": "unknown", "success": False, "error": "缺少文件名"})
            continue

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": f"不支持的文件格式 {ext}，仅支持 .txt / .doc / .docx",
            })
            continue

        try:
            content = await file.read()
            file_id = str(uuid.uuid4())
            bucket_name = settings.tts_bucket
            blob_name = f"vigloo-tts-uploads/files/source/{file_id}/{file.filename}"
            gcs_path = f"gs://{bucket_name}/{blob_name}"

            content_type = file.content_type or "application/octet-stream"
            upload_bytes(blob_name, content, content_type, bucket_name=bucket_name)

            display_name = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename

            meta = {
                "file_id": file_id,
                "display_name": display_name,
                "original_filename": file.filename,
                "gcs_path": gcs_path,
                "gcs_blob_name": blob_name,
                "file_size": len(content),
                "file_extension": ext,
                "content_type": content_type,
                "uploaded_at": datetime.now().isoformat(),
            }
            _tts_files[file_id] = meta
            _save_tts_file_meta(meta)

            logger.info(f"TTS源文件批量上传成功: {file_id} -> {gcs_path}")

            results.append({
                "filename": file.filename,
                "success": True,
                "file_id": file_id,
                "display_name": display_name,
                "gcs_path": gcs_path,
                "size": len(content),
            })
        except Exception as e:
            logger.error(f"TTS源文件批量上传失败 ({file.filename}): {e}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e),
            })

    success_count = sum(1 for r in results if r.get("success"))
    fail_count = sum(1 for r in results if not r.get("success"))

    return {
        "total": len(results),
        "success_count": success_count,
        "fail_count": fail_count,
        "results": results,
    }


@router.patch("/files/{file_id}")
async def rename_tts_source_file(file_id: str, payload: dict):
    """重命名 TTS 源文件的显示名称"""
    _load_all_tts_files()

    new_name = payload.get("display_name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="请输入新名称")

    meta = _tts_files.get(file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="文件不存在")

    meta["display_name"] = new_name
    _tts_files[file_id] = meta
    _save_tts_file_meta(meta)

    return {
        "file_id": file_id,
        "display_name": new_name,
        "message": "重命名成功",
    }


@router.get("/preview/{voice_id}")
async def preview_voice(voice_id: str):
    """音色试听（固定示例文本）"""
    try:
        import edge_tts

        sample_text = "你好，这是语音试听示例。"
        rate_str = "+0%"

        communicate = edge_tts.Communicate(
            text=sample_text,
            voice=voice_id,
            rate=rate_str,
            pitch="+0Hz",
            volume="+0%",
        )

        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        # 临时上传到 GCS
        preview_id = str(uuid.uuid4())
        blob_name = f"vigloo-tts-uploads/preview/{preview_id}.mp3"
        upload_bytes(blob_name, bytes(audio_data), "audio/mpeg", bucket_name=settings.tts_bucket)

        # 生成签名 URL（1小时有效）
        preview_url = generate_download_signed_url(
            blob_name=blob_name,
            download_filename=f"preview_{voice_id}.mp3",
            content_type="audio/mpeg",
            bucket_name=settings.tts_bucket,
        )

        return {"preview_url": preview_url}
    except Exception as e:
        logger.error(f"音色试听失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-custom")
async def preview_custom(
    voice_id: str = Form(...),
    rate: float = Form(1.0),
    pitch: str = Form("+0Hz"),
    volume: str = Form("+0%"),
    text: str = Form(None),
    file_id: str = Form(None),
    gcs_path: str = Form(None),
):
    """自定义试听（用户文本 + 音色配置）"""
    try:
        import edge_tts

        # 获取文本
        actual_text = ""
        if text and text.strip():
            actual_text = text.strip()[:200]  # 限制200字
        elif file_id:
            _load_all_tts_files()
            meta = _tts_files.get(file_id)
            if meta:
                blob_name = meta["gcs_blob_name"]
                bucket, _ = get_bucket(settings.tts_bucket)
                blob = bucket.blob(blob_name)
                content = blob.download_as_bytes()
                ext = meta.get("file_extension", ".txt").lower()
                if ext == ".txt":
                    actual_text = content.decode("utf-8")[:200]
                elif ext == ".docx":
                    actual_text = _extract_docx_text(content)[:200]
        elif gcs_path:
            path = gcs_path.replace("gs://", "")
            bucket_name_part = path.split("/", 1)[0]
            blob_name = path.split("/", 1)[1] if "/" in path else ""
            bucket, _ = get_bucket(bucket_name_part)
            blob = bucket.blob(blob_name)
            content = blob.download_as_bytes()
            actual_text = content.decode("utf-8")[:200]

        if not actual_text:
            actual_text = "你好，这是语音试听示例。"

        rate_str = f"+{int((rate - 1) * 100)}%" if rate >= 1 else f"{int((rate - 1) * 100)}%"

        communicate = edge_tts.Communicate(
            text=actual_text,
            voice=voice_id,
            rate=rate_str,
            pitch=pitch,
            volume=volume,
        )

        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        preview_id = str(uuid.uuid4())
        blob_name = f"vigloo-tts-uploads/preview/{preview_id}.mp3"
        upload_bytes(blob_name, bytes(audio_data), "audio/mpeg", bucket_name=settings.tts_bucket)

        preview_url = generate_download_signed_url(
            blob_name=blob_name,
            download_filename=f"preview.mp3",
            content_type="audio/mpeg",
            bucket_name=settings.tts_bucket,
        )

        return {"preview_url": preview_url}
    except Exception as e:
        logger.error(f"自定义试听失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-dialogue-custom")
async def preview_dialogue_custom(req: DialogueRequest):
    """多角色对话试听"""
    try:
        from pydub import AudioSegment

        segments = _parse_dialogue_text(req.text)
        if not segments:
            raise HTTPException(status_code=400, detail="未解析到对话内容")

        # 只取前3段试听
        preview_segments = segments[:3]

        silence = AudioSegment.silent(duration=req.silence_gap)
        combined = AudioSegment.empty()

        for seg in preview_segments:
            role = seg["role"]
            cfg = req.role_voices.get(role)
            if not cfg:
                continue

            audio_bytes = await _generate_segment_audio(
                seg["text"], cfg.voice_id, cfg.rate, cfg.pitch, cfg.volume
            )
            seg_audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            combined += seg_audio + silence

        buf = io.BytesIO()
        combined.export(buf, format="mp3")
        buf.seek(0)

        preview_id = str(uuid.uuid4())
        blob_name = f"vigloo-tts-uploads/preview/{preview_id}.mp3"
        upload_bytes(blob_name, buf.read(), "audio/mpeg", bucket_name=settings.tts_bucket)

        preview_url = generate_download_signed_url(
            blob_name=blob_name,
            download_filename=f"dialogue_preview.mp3",
            content_type="audio/mpeg",
            bucket_name=settings.tts_bucket,
        )

        return {"preview_url": preview_url}
    except Exception as e:
        logger.error(f"对话试听失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert-from-file")
async def convert_from_gcs_file(
    background_tasks: BackgroundTasks,
    file_id: str = Form(None),
    gcs_path: str = Form(None),
    text: str = Form(None),
    voice_id: str = Form(...),
    rate: float = Form(1.0),
    pitch: str = Form("+0Hz"),
    volume: str = Form("+0%"),
    output_format: str = Form("mp3"),
    filename: Optional[str] = Form(None),
):
    """从 GCS 源文件或直接文本创建 TTS 任务"""
    # 获取文本内容
    actual_text = ""

    if text and text.strip():
        actual_text = text.strip()
    elif file_id:
        _load_all_tts_files()
        meta = _tts_files.get(file_id)
        if not meta:
            raise HTTPException(status_code=404, detail="源文件不存在")
        # 从 GCS 读取文件内容
        try:
            blob_name = meta["gcs_blob_name"]
            bucket, _ = get_bucket(settings.tts_bucket)
            blob = bucket.blob(blob_name)
            content = blob.download_as_bytes()
            ext = meta.get("file_extension", ".txt").lower()
            if ext == ".txt":
                actual_text = content.decode("utf-8")
            elif ext == ".docx":
                try:
                    actual_text = _extract_docx_text(content)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f".docx 文件解析失败: {str(e)}")
            elif ext == ".doc":
                raise HTTPException(status_code=400, detail="不支持旧版 .doc 格式，请转换为 .docx 后重试")
            if not filename:
                filename = meta.get("display_name", meta.get("original_filename", ""))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取源文件失败: {str(e)}")
    elif gcs_path:
        try:
            # 从任意 GCS 路径读取
            path = gcs_path.replace("gs://", "")
            bucket_name_part = path.split("/", 1)[0]
            blob_name = path.split("/", 1)[1] if "/" in path else ""
            bucket, _ = get_bucket(bucket_name_part)
            blob = bucket.blob(blob_name)
            content = blob.download_as_bytes()
            actual_text = content.decode("utf-8")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取GCS文件失败: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="请提供文本内容、源文件ID或GCS路径")

    if not actual_text.strip():
        raise HTTPException(status_code=400, detail="文本内容为空")

    # 创建 TTS 任务
    task_id = str(uuid.uuid4())
    bucket_name = settings.tts_bucket

    tts_tasks[task_id] = {
        "task_id": task_id,
        "text": actual_text[:100] + "..." if len(actual_text) > 100 else actual_text,
        "status": "pending",
        "progress": 0.0,
        "voice_id": voice_id,
        "rate": rate,
        "pitch": pitch,
        "volume": volume,
        "output_format": output_format,
        "created_at": datetime.now().isoformat(),
        "audio_file": None,
        "filename": filename,
        "gcs_path": f"gs://{bucket_name}/vigloo-tts-uploads/outputs/{task_id}.{output_format}",
    }
    _save_tts_task_meta(tts_tasks[task_id])

    background_tasks.add_task(
        _process_tts_task, task_id, actual_text, voice_id, rate, pitch, volume, output_format,
    )

    return {
        "task_id": task_id,
        "message": "TTS 任务已创建",
        "status": "pending",
    }
