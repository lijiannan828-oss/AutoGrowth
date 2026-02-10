"""Cloud Run job responsible for bundling files into a temporary ZIP."""

from __future__ import annotations

import os
import sys
import tempfile
import zipfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from google.cloud import storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.config import settings
from app.core.firestore import get_firestore_client, init_firestore

COLLECTION_NAME = "zip_tasks"


def _log(message: str) -> None:
    print(f"[zip-worker] {message}", flush=True)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少必要的环境变量：{name}")
    return value


def _parse_gs_path(path: str) -> Tuple[str, str]:
    if not path or not path.startswith("gs://"):
        raise ValueError(f"无效的 GCS 路径：{path}")
    remainder = path[5:]
    if "/" not in remainder:
        raise ValueError(f"缺少对象路径：{path}")
    bucket, blob_name = remainder.split("/", 1)
    if not bucket or not blob_name:
        raise ValueError(f"缺少 bucket 或对象：{path}")
    return bucket, blob_name


class ZipTaskRunner:
    def __init__(self) -> None:
        init_firestore()
        self.firestore = get_firestore_client()
        self.storage_client = storage.Client()
        self.task_id = _require_env("ZIP_TASK_ID")
        self.task_ref = self.firestore.collection(COLLECTION_NAME).document(self.task_id)
        snapshot = self.task_ref.get()
        if not snapshot.exists:
            raise RuntimeError(f"zip_tasks 文档 {self.task_id} 不存在")
        self.task_data = snapshot.to_dict() or {}
        self.paths: List[str] = self.task_data.get("paths") or []
        if not self.paths:
            raise RuntimeError("zip 任务缺少 paths 列表")
        self.zip_bucket = (
            self.task_data.get("zip_bucket")
            or settings.pipeline_temp_download_bucket
            or "vigloo-temp-downloads"
        )
        self.zip_object = (
            self.task_data.get("zip_object") or f"zip/{self.task_id}.zip"
        )

    def run(self) -> None:
        self.task_ref.update(
            {
                "status": "PROCESSING",
                "status_message": "正在下载文件并准备打包",
                "progress": 0,
                "updated_at": SERVER_TIMESTAMP,
            }
        )

        with tempfile.TemporaryDirectory(prefix="zip-task-") as tmpdir:
            download_root = Path(tmpdir) / "files"
            download_root.mkdir(parents=True, exist_ok=True)
            
            # 下载文件阶段 (0% -> 80%)，按照文件数量计算
            # Note: _download_all will handle progress updates internally
            downloaded_files = self._download_all(download_root)
            if not downloaded_files:
                raise RuntimeError("未下载到任何文件，无法创建 ZIP")
            
            # 打包阶段 (80% -> 90%)
            self.task_ref.update({
                "status_message": f"正在打包 {len(downloaded_files)} 个文件...",
                "progress": 80,
                "updated_at": SERVER_TIMESTAMP,
            })
            zip_path = Path(tmpdir) / "bundle.zip"
            self._create_zip(downloaded_files, zip_path, download_root)
            
            # 上传阶段 (90% -> 100%)
            self.task_ref.update({
                "status_message": "正在上传 ZIP 文件...",
                "progress": 90,
                "updated_at": SERVER_TIMESTAMP,
            })
            result = self._upload_zip(zip_path)
            
            # 完成 (100%)
            self.task_ref.update({
                "status_message": "ZIP 文件已就绪",
                "progress": 100,
                "updated_at": SERVER_TIMESTAMP,
            })
            self._mark_success(result)
        _log("✅ ZIP 任务完成")

    def _download_all(self, download_root: Path) -> List[Path]:
        # 第一步：解析所有需要下载的 Blob
        self.task_ref.update({
            "status_message": "正在解析文件列表...",
            "progress": 0,
            "updated_at": SERVER_TIMESTAMP,
        })
        blobs_to_download: List[Tuple[storage.Blob, Path]] = []
        
        for idx, user_path in enumerate(self.paths):
            try:
                bucket_name, object_name = _parse_gs_path(user_path)
                bucket = self.storage_client.bucket(bucket_name)
                blob = bucket.blob(object_name)
                
                # Fix: blob.exists() doesn't take parameters
                if blob.exists():
                    local_path = download_root / object_name
                    blobs_to_download.append((blob, local_path))
                    _log(f"✓ 找到文件：{object_name}")
                    continue

                # Treat as directory prefix
                prefix = object_name.rstrip("/") + "/"
                _log(f"📁 作为目录处理：{prefix}")
                blobs = list(
                    self.storage_client.list_blobs(bucket_name, prefix=prefix)
                )
                if not blobs:
                    _log(f"⚠️ 未找到路径：{user_path}，跳过")
                    continue
                    
                _log(f"📁 找到 {len(blobs)} 个文件在目录中")
                for folder_blob in blobs:
                    relative = Path(folder_blob.name)
                    local_path = download_root / relative
                    blobs_to_download.append((folder_blob, local_path))
                    
                # Update progress during parsing
                if (idx + 1) % max(1, len(self.paths) // 4) == 0:
                    self.task_ref.update({
                        "status_message": f"正在解析文件列表... ({idx + 1}/{len(self.paths)})",
                        "progress": int((idx + 1) / len(self.paths) * 5),
                        "updated_at": SERVER_TIMESTAMP,
                    })
            except Exception as exc:
                _log(f"❌ 解析路径失败 {user_path}: {exc}")
                continue

        total_files = len(blobs_to_download)
        if total_files == 0:
            self.task_ref.update({
                "status_message": "未找到任何文件",
                "progress": 0,
                "updated_at": SERVER_TIMESTAMP,
            })
            return []

        # Update status after parsing complete
        self.task_ref.update({
            "status_message": f"已找到 {total_files} 个文件，开始下载...",
            "progress": 5,
            "updated_at": SERVER_TIMESTAMP,
        })
        _log(f"✅ 解析完成，共 {total_files} 个文件需要下载")

        # 第二步：并行下载文件并更新进度（带速度追踪）
        downloaded: List[Path] = []
        _log(f"开始并行下载 {total_files} 个文件...")
        
        # Calculate total size for progress tracking
        total_size_bytes = sum(blob.size or 0 for blob, _ in blobs_to_download)
        _log(f"📊 总大小: {total_size_bytes / (1024*1024):.1f} MB")
        
        # Track download progress
        download_start_time = time.time()
        last_update_time = download_start_time
        last_update_bytes = 0
        
        # Helper function for single file download with chunked download and progress
        def download_one(blob_item: Tuple[storage.Blob, Path]) -> Tuple[Path, int]:
            """Download a single file and return (path, bytes_downloaded)"""
            blob, local_path = blob_item
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use chunked download instead of download_to_filename for better progress tracking
            # and to handle large files without timeout issues
            chunk_size = 8 * 1024 * 1024  # 8MB chunks
            file_bytes = 0
            
            try:
                with blob.open("rb") as reader, local_path.open("wb") as writer:
                    while True:
                        chunk = reader.read(chunk_size)
                        if not chunk:
                            break
                        writer.write(chunk)
                        file_bytes += len(chunk)
            except Exception as exc:
                _log(f"❌ 下载失败 {blob.name}: {exc}")
                raise
            
            return local_path, file_bytes

        import concurrent.futures
        import threading
        
        # Use ThreadPoolExecutor for I/O bound tasks
        # Max workers = 10 to avoid overwhelming network/CPU
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks and track them
            future_to_blob = {}
            for blob_item in blobs_to_download:
                blob, local_path = blob_item
                future = executor.submit(download_one, blob_item)
                future_to_blob[future] = blob_item
            
            # Update status after submitting all tasks
            self.task_ref.update({
                "status_message": f"正在下载 (0/{total_files}): 开始下载...",
                "progress": 5,
                "speed_bps": 0,
                "estimated_seconds": None,
                "updated_at": SERVER_TIMESTAMP,
            })
            _log(f"📥 已提交 {len(future_to_blob)} 个下载任务")
            
            # Track progress with thread-safe variables
            completed_count = 0
            failed_count = 0
            downloaded_bytes = 0  # Initialize here for thread safety
            progress_lock = threading.Lock()
            stop_progress_thread = threading.Event()
            
            # Background thread to update progress periodically
            def update_progress_periodically():
                """Periodically update progress even if no files completed yet"""
                while not stop_progress_thread.is_set():
                    time.sleep(3)  # Update every 3 seconds
                    if stop_progress_thread.is_set():
                        break
                    
                    with progress_lock:
                        current_completed = completed_count
                        current_downloaded_bytes = downloaded_bytes
                    
                    # Only update if we have some progress
                    if current_completed > 0 or current_downloaded_bytes > 0:
                        current_time = time.time()
                        elapsed_time = current_time - download_start_time
                        
                        if elapsed_time > 0:
                            current_speed_bps = current_downloaded_bytes / elapsed_time
                        else:
                            current_speed_bps = 0
                        
                        remaining_bytes = total_size_bytes - current_downloaded_bytes
                        estimated_seconds = None
                        if current_speed_bps > 0 and remaining_bytes > 0:
                            estimated_seconds = int(remaining_bytes / current_speed_bps)
                        
                        # 下载进度：5% 到 80%，按照文件数量计算
                        percent = 5 + int((current_completed / total_files) * 75) if total_files > 0 else 5
                        speed_mbps = current_speed_bps / (1024 * 1024)
                        speed_str = f"{speed_mbps:.1f} MB/s" if speed_mbps > 0 else "计算中..."
                        
                        eta_str = ""
                        if estimated_seconds is not None:
                            if estimated_seconds < 60:
                                eta_str = f"，预计 {estimated_seconds} 秒"
                            elif estimated_seconds < 3600:
                                eta_str = f"，预计 {estimated_seconds // 60} 分钟"
                            else:
                                eta_str = f"，预计 {estimated_seconds // 3600} 小时 {(estimated_seconds % 3600) // 60} 分钟"
                        
                        status_msg = f"正在下载 ({current_completed}/{total_files}): {speed_str}{eta_str}"
                        
                        try:
                            self.task_ref.update({
                                "status_message": status_msg,
                                "progress": percent,
                                "speed_bps": int(current_speed_bps),
                                "estimated_seconds": estimated_seconds,
                                "downloaded_bytes": current_downloaded_bytes,
                                "total_bytes": total_size_bytes,
                                "updated_at": SERVER_TIMESTAMP,
                            })
                        except Exception as exc:
                            _log(f"⚠️ 更新进度失败：{exc}")
            
            # Start progress update thread
            progress_thread = threading.Thread(target=update_progress_periodically, daemon=True)
            progress_thread.start()
            
            try:
                for future in concurrent.futures.as_completed(future_to_blob):
                    blob_item = future_to_blob[future]
                    blob, local_path = blob_item
                    blob_name = blob.name if blob else local_path.name
                    
                    try:
                        path, file_bytes = future.result()
                        downloaded.append(path)
                        with progress_lock:
                            completed_count += 1
                            downloaded_bytes += file_bytes
                            current_completed = completed_count
                            current_downloaded_bytes = downloaded_bytes
                        
                        # Calculate speed and ETA
                        current_time = time.time()
                        elapsed_time = current_time - download_start_time
                        
                        # Calculate speed (bytes per second) using recent progress
                        recent_time = current_time - last_update_time
                        recent_bytes = current_downloaded_bytes - last_update_bytes
                        
                        if recent_time > 0:
                            current_speed_bps = recent_bytes / recent_time
                        elif elapsed_time > 0:
                            current_speed_bps = current_downloaded_bytes / elapsed_time
                        else:
                            current_speed_bps = 0
                        
                        # Estimate remaining time
                        remaining_bytes = total_size_bytes - current_downloaded_bytes
                        estimated_seconds = None
                        if current_speed_bps > 0 and remaining_bytes > 0:
                            estimated_seconds = int(remaining_bytes / current_speed_bps)
                        
                        # Update progress more frequently - every file
                        # 下载进度：5% 到 80%，按照文件数量计算
                        percent = 5 + int((current_completed / total_files) * 75) if total_files > 0 else 5
                        # Show current file name for better feedback
                        current_file = Path(blob_name).name if blob_name else "unknown"
                        
                        # Format speed display
                        speed_mbps = current_speed_bps / (1024 * 1024)
                        speed_str = f"{speed_mbps:.1f} MB/s" if speed_mbps > 0 else "计算中..."
                        
                        # Format ETA
                        eta_str = ""
                        if estimated_seconds is not None:
                            if estimated_seconds < 60:
                                eta_str = f"，预计 {estimated_seconds} 秒"
                            elif estimated_seconds < 3600:
                                eta_str = f"，预计 {estimated_seconds // 60} 分钟"
                            else:
                                eta_str = f"，预计 {estimated_seconds // 3600} 小时 {(estimated_seconds % 3600) // 60} 分钟"
                        
                        status_msg = f"正在下载 ({current_completed}/{total_files}): {current_file} ({speed_str}{eta_str})"
                        
                        self.task_ref.update({
                            "status_message": status_msg,
                            "progress": percent,
                            "speed_bps": int(current_speed_bps),
                            "estimated_seconds": estimated_seconds,
                            "downloaded_bytes": current_downloaded_bytes,
                            "total_bytes": total_size_bytes,
                            "updated_at": SERVER_TIMESTAMP,
                        })
                        _log(f"⬇️ [{current_completed}/{total_files}] 下载完成：{current_file} ({speed_mbps:.1f} MB/s)")
                        
                        # Update tracking variables
                        last_update_time = current_time
                        last_update_bytes = current_downloaded_bytes
                            
                    except Exception as exc:
                        with progress_lock:
                            failed_count += 1
                        error_msg = str(exc)
                        _log(f"❌ 下载失败 {blob_name}: {error_msg}")
                        # Update status with error info but don't fail the whole task
                        with progress_lock:
                            current_completed = completed_count
                            current_failed = failed_count
                        self.task_ref.update({
                            "status_message": f"下载中 ({current_completed}/{total_files})，失败: {current_failed}",
                            "updated_at": SERVER_TIMESTAMP,
                        })
            finally:
                # Stop progress update thread
                stop_progress_thread.set()
                progress_thread.join(timeout=1)
            
            with progress_lock:
                final_failed_count = failed_count
            if final_failed_count > 0:
                _log(f"⚠️ 有 {final_failed_count} 个文件下载失败")
            
        _log(f"✅ 下载完成，成功: {len(downloaded)}, 失败: {failed_count}")
        return downloaded

    def _create_zip(
        self,
        downloaded_files: Iterable[Path],
        zip_path: Path,
        download_root: Path,
    ) -> None:
        _log(f"🗜️ 打包 ZIP：{zip_path}")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in downloaded_files:
                arcname = file_path.relative_to(download_root)
                zf.write(file_path, arcname=str(arcname))

    def _upload_zip(self, zip_path: Path) -> Dict[str, str | int | float]:
        bucket = self.storage_client.bucket(self.zip_bucket)
        blob = bucket.blob(self.zip_object)
        _log(
            f"⬆️ 上传 ZIP 到 gs://{self.zip_bucket}/{self.zip_object} (size={zip_path.stat().st_size} bytes)"
        )
        blob.metadata = {
            "zip_task_id": self.task_id,
            "source": "pipeline-download",
        }
        blob.upload_from_filename(zip_path)

        # Set custom_time for lifecycle rules (if configured)
        try:
            blob.custom_time = datetime.now(timezone.utc)
            blob.patch()
        except Exception as exc:  # pragma: no cover - lifecycle optional
            _log(f"⚠️ 无法设置 custom_time：{exc}")

        expires_at = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(hours=24)
        try:
            download_url = blob.generate_signed_url(expiration=timedelta(hours=24))
        except Exception:
            download_url = None

        return {
            "zip_gcs_path": f"gs://{self.zip_bucket}/{self.zip_object}",
            "zip_size_bytes": zip_path.stat().st_size,
            "download_url": download_url,
            "expires_at": expires_at,
        }

    def _mark_success(self, result: Dict[str, str | int | float]) -> None:
        self.task_ref.update(
            {
                "status": "COMPLETE",
                "status_message": "ZIP 已生成",
                "progress": 100,
                **result,
                "updated_at": SERVER_TIMESTAMP,
            }
        )


def main() -> None:
    try:
        runner = ZipTaskRunner()
        runner.run()
    except Exception as exc:
        _log(f"❌ Zip Worker 执行失败：{exc}")
        firestore = get_firestore_client()
        task_id = os.environ.get("ZIP_TASK_ID")
        if task_id:
            firestore.collection(COLLECTION_NAME).document(task_id).update(
                {
                    "status": "FAILED",
                    "status_message": str(exc),
                    "updated_at": SERVER_TIMESTAMP,
                }
            )
        raise


if __name__ == "__main__":
    main()


