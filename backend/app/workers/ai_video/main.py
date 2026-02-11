"""AI Video Worker — runs as a Cloud Run Job.

Architecture mirrors the fission worker:
  1. Reads task config from Firestore ``ai_video_jobs/{task_id}``
  2. Calls the external AI video generation API (placeholder – TODO)
  3. Uploads the generated video & thumbnail to GCS
  4. Updates Firestore with output paths and signed URLs

Usage (Cloud Run Job override):
    python -m app.workers.ai_video.main <task_id>
"""

import json
import os
import subprocess
import sys
import tempfile
import traceback
from typing import Dict, Any

from google.cloud import firestore, storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


def get_firestore_client():
    """获取 Firestore 客户端"""
    project_id = os.environ.get("FIRESTORE_PROJECT_ID") or os.environ.get("GCP_PROJECT_ID")
    return firestore.Client(project=project_id)


class AIVideoWorker:
    """AI 视频生成 Worker（与裂变 Worker 架构一致）"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.firestore = get_firestore_client()
        self.storage_client = storage.Client()
        self.doc_ref = self.firestore.collection("ai_video_jobs").document(task_id)
        self.output_bucket = os.environ.get("FISSION_UPLOAD_BUCKET", "vigloo-fission-uploads")

    def process(self) -> None:
        """处理 AI 视频生成任务"""
        try:
            # 获取任务信息
            doc = self.doc_ref.get()
            if not doc.exists:
                raise ValueError(f"Task {self.task_id} not found in Firestore")

            task_data = doc.to_dict()

            # 更新状态为 PROCESSING
            self.doc_ref.update({
                "status": "processing",
                "progress": 10,
                "progress_text": "正在生成视频...",
                "updated_at": SERVER_TIMESTAMP,
            })
            print(f"[INFO] Task {self.task_id} status → PROCESSING")

            full_prompt = task_data.get("full_prompt", task_data.get("prompt", ""))
            style = task_data.get("style", "realistic")
            duration = task_data.get("duration", 5)
            aspect_ratio = task_data.get("aspect_ratio", "9:16")

            print(f"[INFO] Prompt: {full_prompt[:100]}...")
            print(f"[INFO] Style: {style}, Duration: {duration}s, Ratio: {aspect_ratio}")

            # ------------------------------------------------------------------
            # TODO: 接入实际的 AI 视频生成 API
            # 可选方案：
            #   - Runway Gen-2/Gen-3
            #   - Pika Labs
            #   - Stable Video Diffusion
            #   - 智谱清影 / 阿里通义千问视频 / 字节即梦
            #
            # 实现步骤：
            #   1. 调用 API 提交生成请求
            #   2. 轮询等待生成完成
            #   3. 下载生成的视频到本地临时目录
            #   4. 上传到 GCS
            # ------------------------------------------------------------------

            self.doc_ref.update({"progress": 30, "updated_at": SERVER_TIMESTAMP})

            with tempfile.TemporaryDirectory() as temp_dir:
                # 生成占位视频（黑屏 + 提示文字）用于演示流程
                local_video = os.path.join(temp_dir, f"{self.task_id}.mp4")
                self._generate_placeholder_video(local_video, full_prompt, duration, aspect_ratio)

                self.doc_ref.update({"progress": 60, "updated_at": SERVER_TIMESTAMP})

                # 上传视频到 GCS
                video_gcs_path = f"ai-video/outputs/{self.task_id}.mp4"
                self._upload_to_gcs(local_video, video_gcs_path)

                self.doc_ref.update({"progress": 80, "updated_at": SERVER_TIMESTAMP})

                # 生成缩略图并上传
                local_thumb = os.path.join(temp_dir, f"{self.task_id}.jpg")
                self._generate_thumbnail(local_video, local_thumb)
                thumb_gcs_path = f"ai-video/outputs/{self.task_id}.jpg"
                self._upload_to_gcs(local_thumb, thumb_gcs_path)

            # 生成签名 URL
            video_url = self._generate_signed_url(video_gcs_path)
            thumbnail_url = self._generate_signed_url(thumb_gcs_path)

            # 更新 Firestore 为完成
            self.doc_ref.update({
                "status": "completed",
                "progress": 100,
                "progress_text": "视频生成完成",
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "video_gcs_path": f"gs://{self.output_bucket}/{video_gcs_path}",
                "thumbnail_gcs_path": f"gs://{self.output_bucket}/{thumb_gcs_path}",
                "completed_at": SERVER_TIMESTAMP,
                "updated_at": SERVER_TIMESTAMP,
            })
            print(f"[INFO] Task {self.task_id} → COMPLETED")

        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[ERROR] Task {self.task_id} failed: {error_msg}")
            self.doc_ref.update({
                "status": "failed",
                "error_message": str(e),
                "progress_text": f"生成失败: {str(e)[:100]}",
                "completed_at": SERVER_TIMESTAMP,
                "updated_at": SERVER_TIMESTAMP,
            })


    # ----------------------------------------------- 辅助方法

    def _generate_placeholder_video(
        self, output_path: str, prompt: str, duration: int, aspect_ratio: str
    ) -> None:
        """生成占位视频（黑底 + 白色提示文字）。

        当接入真实 AI API 后，这里应替换为下载 API 返回的视频文件。
        """
        # 解析宽高
        if aspect_ratio == "16:9":
            width, height = 1280, 720
        elif aspect_ratio == "1:1":
            width, height = 720, 720
        else:  # 默认 9:16
            width, height = 720, 1280

        # 截取 prompt 前40字（避免 ffmpeg drawtext 过长）
        safe_text = prompt[:40].replace("'", "").replace('"', '').replace("\\", "")

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={width}x{height}:d={duration}:r=24",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-vf", (
                f"drawtext=text='AI Video Placeholder':fontsize=36:"
                f"fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-40,"
                f"drawtext=text='{safe_text}':fontsize=20:"
                f"fontcolor=gray:x=(w-text_w)/2:y=(h-text_h)/2+40"
            ),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-shortest",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg placeholder failed: {result.stderr[-500:]}")
        print(f"[INFO] Placeholder video created: {output_path}")

    def _generate_thumbnail(self, video_path: str, output_path: str) -> None:
        """从视频第1秒提取缩略图"""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", "00:00:01",
            "-vframes", "1",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Thumbnail generation failed: {result.stderr[-300:]}")
        print(f"[INFO] Thumbnail created: {output_path}")

    def _upload_to_gcs(self, local_path: str, blob_name: str) -> None:
        """上传文件到 GCS"""
        bucket = self.storage_client.bucket(self.output_bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        print(f"[INFO] Uploaded to gs://{self.output_bucket}/{blob_name}")

    def _generate_signed_url(self, blob_name: str, expiration_hours: int = 1) -> str:
        """生成 GCS 签名 URL"""
        from datetime import timedelta
        bucket = self.storage_client.bucket(self.output_bucket)
        blob = bucket.blob(blob_name)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET",
        )


def main():
    """Worker 入口"""
    if len(sys.argv) < 2:
        print("Usage: python -m app.workers.ai_video.main <task_id>")
        sys.exit(1)

    task_id = sys.argv[1]
    print(f"[INFO] Starting AI Video Worker for task {task_id}")

    worker = AIVideoWorker(task_id)
    worker.process()


if __name__ == "__main__":
    main()