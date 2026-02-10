"""Video processing utilities for fission material generation."""

import os
import random
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from google.cloud import storage


class VideoProcessor:
    """视频处理工具类"""

    def __init__(self):
        self.storage_client = storage.Client()

    def download_from_gcs(self, gcs_path: str, local_path: str) -> None:
        """从GCS下载文件"""
        bucket_name, blob_name = self._parse_gcs_path(gcs_path)
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(local_path)

    def upload_to_gcs(self, local_path: str, gcs_path: str) -> None:
        """上传文件到GCS"""
        bucket_name, blob_name = self._parse_gcs_path(gcs_path)
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)

    def get_video_info(self, video_path: str) -> dict:
        """获取视频信息"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        
        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration": duration,
        }

    def apply_filter(self, input_path: str, output_path: str, filter_preset: str) -> None:
        """应用滤镜效果"""
        filter_map = {
            "warm": "eq=saturation=1.3:brightness=0.05,colorbalance=rs=0.1:gs=-0.05:bs=-0.1",
            "cool": "eq=saturation=1.2:brightness=-0.02,colorbalance=rs=-0.1:gs=0.05:bs=0.1",
            "vintage": "eq=contrast=1.1:saturation=0.8",
            "high_contrast": "eq=contrast=1.4:brightness=0.02:saturation=1.1",
            "soft": "gblur=sigma=0.5,eq=contrast=0.9:brightness=0.05",
        }

        vf = filter_map.get(filter_preset, "null")
        cmd = [
            "ffmpeg", "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264",  # 使用H.264编码
            "-preset", "fast",   # 快速编码
            "-crf", "23",        # 质量控制
            "-c:a", "aac",       # 音频编码
            "-b:a", "128k",      # 音频比特率
            "-movflags", "+faststart",  # 优化流媒体播放
            "-y", output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def adjust_duration(
        self, input_path: str, output_path: str, variance_percent: int
    ) -> float:
        """调整视频时长（通过改变播放速度）"""
        info = self.get_video_info(input_path)
        original_duration = info["duration"]

        # 随机选择加速或减速
        speed_factor = 1.0 + random.uniform(-variance_percent/100, variance_percent/100)
        speed_factor = max(0.5, min(2.0, speed_factor))  # 限制在0.5x-2.0x之间

        cmd = [
            "ffmpeg", "-i", input_path,
            "-filter_complex", f"[0:v]setpts={1/speed_factor}*PTS[v];[0:a]atempo={speed_factor}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y", output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        return original_duration * (1 / speed_factor)

    def frame_shuffle(self, input_path: str, output_path: str, shuffle_intensity: float = 0.3) -> None:
        """抽帧重组（保持整体连贯性）"""
        info = self.get_video_info(input_path)
        total_frames = info["frame_count"]
        
        # 计算要保留的帧
        keep_ratio = 1.0 - (shuffle_intensity * 0.5)  # 保留70%-100%的帧
        frames_to_keep = int(total_frames * keep_ratio)
        
        # 生成帧选择列表（保持大致顺序但有随机性）
        segment_size = max(10, total_frames // 20)
        selected_frames = []
        
        for i in range(0, total_frames, segment_size):
            segment_end = min(i + segment_size, total_frames)
            segment_frames = list(range(i, segment_end))
            # 在每个片段内随机选择帧
            keep_count = int(len(segment_frames) * keep_ratio)
            selected = sorted(random.sample(segment_frames, keep_count))
            selected_frames.extend(selected)
        
        # 使用ffmpeg的select滤镜
        frame_expr = "+".join([f"eq(n\\,{f})" for f in selected_frames[:100]])  # 限制表达式长度
        
        cmd = [
            "ffmpeg", "-i", input_path,
            "-vf", f"select='{frame_expr}',setpts=N/FRAME_RATE/TB",
            "-af", "aselect='1',asetpts=N/SR/TB",
            "-y", output_path
        ]
        
        # 如果表达式太长，使用简单的抽帧方式
        if len(selected_frames) > 100:
            cmd = [
                "ffmpeg", "-i", input_path,
                "-vf", f"select='not(mod(n\\,{int(1/keep_ratio)}))',setpts=N/FRAME_RATE/TB",
                "-y", output_path
            ]
        
        subprocess.run(cmd, check=True, capture_output=True)

    def add_sticker(
        self, input_path: str, output_path: str, sticker_path: str,
        x_percent: float, y_percent: float, scale: float,
        start_time: Optional[float] = None, end_time: Optional[float] = None
    ) -> None:
        """添加贴纸"""
        # 构建overlay滤镜
        overlay_filter = f"overlay=W*{x_percent/100}:H*{y_percent/100}"
        
        if start_time is not None or end_time is not None:
            enable_expr = "enable="
            if start_time is not None and end_time is not None:
                enable_expr += f"'between(t,{start_time},{end_time})'"
            elif start_time is not None:
                enable_expr += f"'gte(t,{start_time})'"
            else:
                enable_expr += f"'lte(t,{end_time})'"
            overlay_filter += f":{enable_expr}"
        
        cmd = [
            "ffmpeg", "-i", input_path, "-i", sticker_path,
            "-filter_complex", f"[1:v]scale=iw*{scale}:ih*{scale}[sticker];[0:v][sticker]{overlay_filter}",
            "-c:a", "copy",
            "-y", output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _parse_gcs_path(self, gcs_path: str) -> Tuple[str, str]:
        """解析GCS路径"""
        if gcs_path.startswith("gs://"):
            gcs_path = gcs_path[5:]
        parts = gcs_path.split("/", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""

