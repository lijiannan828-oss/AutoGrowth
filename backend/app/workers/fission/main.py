"""Fission worker for video processing.

Supports GCS-based sticker overlays with GIF animation.
Supports automatic subtitle generation with Whisper.
"""

import os
import sys
import subprocess
import tempfile
import traceback
import random
from typing import List, Dict, Any, Optional

from google.cloud import firestore, storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# Whisper 延迟导入（可选功能）
_whisper_model = None

def get_whisper_model(model_name: str = "small"):
    """获取 Whisper 模型（延迟加载）"""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print(f"[INFO] Loading Whisper model: {model_name}")
        _whisper_model = whisper.load_model(model_name)
        print(f"[INFO] Whisper model loaded")
    return _whisper_model


class SubtitleGenerator:
    """字幕生成器 - 使用 Whisper 识别语音并生成 ASS 字幕"""

    @staticmethod
    def generate_subtitle(video_path: str, output_ass_path: str, language: str = None) -> bool:
        """
        从视频生成 ASS 字幕文件

        Args:
            video_path: 视频文件路径
            output_ass_path: 输出 ASS 字幕路径
            language: 语言代码（None 表示自动检测）

        Returns:
            是否成功生成字幕
        """
        try:
            model = get_whisper_model("small")

            print(f"[INFO] Transcribing video: {video_path}")
            result = model.transcribe(
                video_path,
                language=language,
                task="transcribe",
                verbose=False,
                word_timestamps=True,
            )

            # 生成 ASS 字幕
            SubtitleGenerator._write_ass_file(result, output_ass_path)
            print(f"[INFO] Subtitle generated: {output_ass_path}")
            return True

        except Exception as e:
            print(f"[ERROR] Subtitle generation failed: {e}")
            return False

    @staticmethod
    def _write_ass_file(result: dict, output_path: str) -> None:
        """将 Whisper 结果写入 ASS 文件"""
        ass_header = """[Script Info]
Title: Auto Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_header)

            for segment in result.get("segments", []):
                start = SubtitleGenerator._seconds_to_ass_time(segment["start"])
                end = SubtitleGenerator._seconds_to_ass_time(segment["end"])
                text = segment["text"].strip().replace("\n", "\\N")

                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

    @staticmethod
    def _seconds_to_ass_time(seconds: float) -> str:
        """将秒转换为 ASS 时间格式 (h:mm:ss.cc)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def get_firestore_client():
    """获取 Firestore 客户端"""
    project_id = os.environ.get("FIRESTORE_PROJECT_ID") or os.environ.get("GCP_PROJECT_ID")
    return firestore.Client(project=project_id)


class FissionWorker:
    """裂变素材生成Worker"""

    # 贴纸 manifest 缓存
    _sticker_manifest = None

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.firestore = get_firestore_client()
        self.storage_client = storage.Client()
        self.job_ref = self.firestore.collection("fission_jobs").document(job_id)
        self.output_bucket = os.environ.get("FISSION_BUCKET", "vigloo_source")
        self.stickers_base_path = f"gs://{self.output_bucket}/assets/stickers"

    def process(self, task_index: int = 0, task_count: int = 1) -> None:
        """处理裂变任务 - 支持并行分片"""
        try:
            # 获取任务信息
            job_doc = self.job_ref.get()
            if not job_doc.exists:
                raise ValueError(f"Job {self.job_id} not found")

            job_data = job_doc.to_dict()
            variant_count = job_data["variant_count"]
            self.variant_count = variant_count

            # 计算当前任务要处理的变体索引
            my_variants = []
            for i in range(variant_count):
                if i % task_count == task_index:
                    my_variants.append(i)

            print(f"[INFO] Task {task_index} will process variants: {my_variants}")

            # 第一个任务负责更新状态为 PROCESSING
            if task_index == 0:
                self.job_ref.update({
                    "status": "PROCESSING",
                    "progress_text": f"正在处理 ({task_count} 个并行任务)",
                    "updated_at": SERVER_TIMESTAMP,
                })
                print(f"[INFO] Job status updated to PROCESSING")

            # 下载源视频
            source_path = job_data["source_video_path"]
            with tempfile.TemporaryDirectory() as temp_dir:
                local_source = os.path.join(temp_dir, "source.mp4")
                print(f"[INFO] Downloading source video...")
                self._download_from_gcs(source_path, local_source)

                # 获取视频信息
                video_info = self._get_video_info(local_source)
                transforms = job_data["transforms"]

                # 处理分配给当前任务的变体
                failed_variants = []
                for variant_index in my_variants:
                    try:
                        print(f"[INFO] Processing variant {variant_index}")

                        variant = self._generate_variant(
                            local_source,
                            temp_dir,
                            variant_index,
                            transforms,
                            job_data,
                            video_info
                        )

                        # 将变体添加到 Firestore（原子操作）
                        self._add_variant_to_job(variant)

                        # 更新进度
                        self._update_progress()
                        print(f"[INFO] Variant {variant_index} completed")

                    except Exception as variant_err:
                        failed_variants.append(variant_index)
                        print(f"[WARN] Variant {variant_index} failed, skipping: {variant_err}")
                        # 仍然更新进度，让整体进度继续推进
                        self._update_progress()

                if failed_variants:
                    print(f"[WARN] Task {task_index} had {len(failed_variants)} failed variants: {failed_variants}")

                print(f"[INFO] Task {task_index} completed ({len(my_variants) - len(failed_variants)}/{len(my_variants)} succeeded)")

                # 检查是否所有变体都完成了
                self._check_and_complete_job(variant_count)

        except Exception as e:
            error_msg = f"Task {task_index} 失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[ERROR] {error_msg}")
            self._update_task_error(task_index, error_msg)
            raise

    def _download_from_gcs(self, gcs_path: str, local_path: str, max_retries: int = 3) -> None:
        """从 GCS 下载文件（带重试）"""
        import time
        # 解析 gs://bucket/path 格式
        path = gcs_path.replace("gs://", "")
        bucket_name, blob_name = path.split("/", 1)
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        for attempt in range(max_retries):
            try:
                blob.download_to_filename(local_path)
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                    print(f"[WARN] GCS download failed (attempt {attempt + 1}/{max_retries}): {e}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise Exception(f"GCS download failed after {max_retries} attempts: {e}")

    def _download_sticker_from_gcs(self, sticker_path: str, temp_dir: str) -> str:
        """从 GCS 下载贴纸文件，返回本地路径"""
        import os
        import hashlib

        # 确定 GCS 路径
        if sticker_path.startswith("gs://"):
            gcs_path = sticker_path
        elif sticker_path.startswith("/stickers/"):
            # 去掉开头的 /stickers/
            relative_path = sticker_path[10:]
            gcs_path = f"gs://{self.output_bucket}/assets/stickers/{relative_path}"
        else:
            # 假设是相对路径，直接拼接
            gcs_path = f"gs://{self.output_bucket}/assets/stickers/{sticker_path}"

        # 生成本地文件名（使用 hash 避免路径冲突）
        filename = hashlib.md5(gcs_path.encode()).hexdigest() + os.path.splitext(sticker_path)[1]
        local_path = os.path.join(temp_dir, filename)

        try:
            self._download_from_gcs(gcs_path, local_path)
            print(f"[INFO] Downloaded sticker from {gcs_path} to {local_path}")
            return local_path
        except Exception as e:
            print(f"[WARNING] Failed to download sticker from {gcs_path}: {e}")
            return None

    def _load_sticker_manifest(self, temp_dir: str) -> Dict[str, Any]:
        """从 GCS 加载贴纸 manifest.json"""
        if FissionWorker._sticker_manifest is not None:
            return FissionWorker._sticker_manifest

        manifest_path = f"{self.stickers_base_path}/manifest.json"
        local_manifest = os.path.join(temp_dir, "sticker_manifest.json")

        try:
            self._download_from_gcs(manifest_path, local_manifest)
            import json
            with open(local_manifest, 'r', encoding='utf-8') as f:
                FissionWorker._sticker_manifest = json.load(f)
            print(f"[INFO] Loaded sticker manifest with {len(FissionWorker._sticker_manifest.get('stickers', []))} stickers")
            return FissionWorker._sticker_manifest
        except Exception as e:
            print(f"[WARNING] Failed to load sticker manifest: {e}, using default")
            # 返回默认空 manifest
            FissionWorker._sticker_manifest = {"stickers": [], "categories": []}
            return FissionWorker._sticker_manifest

    def _get_sticker_from_manifest(self, sticker_id: str, temp_dir: str) -> Dict[str, Any]:
        """从 manifest 获取贴纸信息并下载到本地"""
        manifest = self._load_sticker_manifest(temp_dir)

        # 查找贴纸
        for sticker in manifest.get("stickers", []):
            if sticker.get("id") == sticker_id:
                # 下载贴纸文件
                gcs_path = f"{self.stickers_base_path}/{sticker['path']}"
                local_path = self._download_sticker_from_gcs(gcs_path, temp_dir)
                if local_path:
                    return {
                        "local_path": local_path,
                        "type": sticker.get("type", "image"),
                        "size": sticker.get("size", 80),
                        "name": sticker.get("name", sticker_id)
                    }
        return None

    def _get_random_sticker_from_gcs(self, category: str, temp_dir: str) -> Dict[str, Any]:
        """从 GCS manifest 随机选择一个贴纸"""
        manifest = self._load_sticker_manifest(temp_dir)
        stickers = manifest.get("stickers", [])

        if category:
            stickers = [s for s in stickers if s.get("category") == category]

        if not stickers:
            print(f"[WARNING] No stickers found for category: {category}")
            return None

        selected = random.choice(stickers)
        return self._get_sticker_from_manifest(selected["id"], temp_dir)

    def _upload_to_gcs(self, local_path: str, gcs_path: str) -> None:
        """上传文件到 GCS"""
        path = gcs_path.replace("gs://", "")
        bucket_name, blob_name = path.split("/", 1)
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)

    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息（包括分辨率）"""
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        import json
        info = json.loads(result.stdout)
        duration = float(info.get("format", {}).get("duration", 0))

        # 获取视频流的分辨率
        width, height = 1080, 1920  # 默认值
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                width = stream.get("width", 1080)
                height = stream.get("height", 1920)
                break

        return {"duration": duration, "width": width, "height": height}

    def _split_video(self, input_path: str, temp_dir: str, segment_duration: int = 120) -> List[str]:
        """将视频切成多段（使用 segment muxer，单次 ffmpeg 调用）

        Args:
            input_path: 输入视频路径
            temp_dir: 临时目录
            segment_duration: 每段时长（秒），默认 120 秒

        Returns:
            切片文件路径列表
        """
        import time
        import glob as glob_mod
        start_time = time.time()

        # 获取视频时长
        video_info = self._get_video_info(input_path)
        duration = video_info["duration"]

        # 如果视频短于 segment_duration，不需要切片
        if duration <= segment_duration:
            print(f"[INFO] Video duration {duration:.1f}s <= {segment_duration}s, no split needed")
            return [input_path]

        num_segments_est = int(duration / segment_duration) + 1
        print(f"[INFO] Splitting {duration:.1f}s video into {num_segments_est} segments")

        # 使用 segment muxer 一次性切片，比循环调用 N 次 ffmpeg 快得多
        pattern = os.path.join(temp_dir, "segment_%03d.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c", "copy",
            "-f", "segment",
            "-segment_time", str(segment_duration),
            "-reset_timestamps", "1",
            "-avoid_negative_ts", "make_zero",
            pattern
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] Segment split failed: {result.stderr[-300:]}")
            raise Exception(f"Segment split failed: {result.stderr[-300:]}")

        segment_files = sorted(glob_mod.glob(os.path.join(temp_dir, "segment_*.mp4")))

        elapsed = time.time() - start_time
        print(f"[INFO] Split completed in {elapsed:.1f}s, {len(segment_files)} segments created")
        return segment_files

    def _concat_segments(self, segment_files: List[str], output_path: str) -> None:
        """合并多个视频片段

        Args:
            segment_files: 片段文件路径列表
            output_path: 输出文件路径
        """
        import time
        start_time = time.time()

        if len(segment_files) == 1:
            # 只有一个片段，直接复制
            subprocess.run(["cp", segment_files[0], output_path], check=True)
            return

        # 创建 concat 文件列表
        concat_list = output_path + ".txt"
        with open(concat_list, "w") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",  # 不重编码
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # 清理 concat 列表文件
        os.remove(concat_list)

        if result.returncode != 0:
            print(f"[ERROR] Concat failed: {result.stderr[-300:]}")
            raise Exception(f"Concat failed: {result.stderr[-300:]}")

        elapsed = time.time() - start_time
        print(f"[INFO] Concat completed in {elapsed:.1f}s")

    def _process_with_segments(
        self,
        input_path: str,
        output_path: str,
        video_filters: List[str],
        audio_filters: List[str],
        temp_dir: str,
        variant_index: int
    ) -> None:
        """分片并行处理长视频

        策略：
        1. 切片（segment muxer，单次 ffmpeg 调用）
        2. 全量并行处理所有片段（ThreadPoolExecutor）
        3. 处理完一次性合并
        """
        import time
        import gc
        from concurrent.futures import ThreadPoolExecutor, as_completed

        total_start = time.time()
        cpu_count = os.cpu_count() or 4
        MAX_WORKERS = int(os.environ.get("FISSION_PARALLEL_SEGMENTS", str(cpu_count)))

        # 根据视频时长动态调整切片大小
        video_info = self._get_video_info(input_path)
        duration = video_info.get("duration", 0)
        if duration > 3600:
            seg_duration = 120  # 超过1小时：120秒切片
        elif duration > 600:
            seg_duration = 60   # 10分钟~1小时：60秒切片
        else:
            seg_duration = 20   # 短视频：20秒切片
        segment_files = self._split_video(input_path, temp_dir, segment_duration=seg_duration)

        if len(segment_files) == 1:
            self._apply_transforms_optimized(input_path, output_path, video_filters, audio_filters)
            return

        total = len(segment_files)
        print(f"[INFO] Processing {total} segments with {MAX_WORKERS} workers")

        def _process_one_segment(seg_idx: int, seg_path: str) -> str:
            """处理单个片段，返回输出路径"""
            print(f"[INFO] Processing segment {seg_idx}/{total}")
            output_seg = os.path.join(temp_dir, f"processed_{variant_index}_{seg_idx:03d}.mp4")
            try:
                self._apply_transforms_optimized(seg_path, output_seg, video_filters, audio_filters)
            finally:
                # 处理完立即删除原始切片释放 tmpfs 内存
                if seg_path != input_path and os.path.exists(seg_path):
                    os.remove(seg_path)
            return output_seg

        # 全量并行处理所有片段
        results = {}
        completed_count = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(_process_one_segment, idx, path): idx
                for idx, path in enumerate(segment_files)
            }
            for future in as_completed(futures):
                seg_idx = futures[future]
                try:
                    output_seg = future.result()
                    results[seg_idx] = output_seg
                    completed_count += 1
                    self._update_segment_progress(variant_index, completed_count, total)
                except Exception as e:
                    print(f"[ERROR] Segment {seg_idx}/{total} failed: {e}")
                    raise

        # 按索引排序，保证合并顺序正确
        processed_files = [results[i] for i in sorted(results.keys())]

        # 一次性合并所有片段
        self._concat_segments(processed_files, output_path)

        # 清理已处理片段文件
        for seg in processed_files:
            if os.path.exists(seg):
                os.remove(seg)
        gc.collect()

        total_elapsed = time.time() - total_start
        print(f"[INFO] Segmented processing completed in {total_elapsed:.1f}s ({total} segments, {MAX_WORKERS} workers)")

    def _generate_variant(
        self,
        source_path: str,
        temp_dir: str,
        variant_index: int,
        transforms: List[Dict[str, Any]],
        job_data: Dict[str, Any],
        video_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成单个变体 - 优化版：一次性应用所有变换"""
        print(f"[DEBUG] Starting variant {variant_index}")
        transforms_applied = []

        # 构建 ffmpeg 滤镜链
        video_filters = []
        audio_filters = []
        speed_factor = 1.0

        print(f"[DEBUG] Building filter chain from {len(transforms)} transforms")

        for idx, transform in enumerate(transforms):
            if not transform.get("enabled", True):
                continue

            transform_type = transform["type"]
            print(f"[DEBUG] Adding transform {idx}: {transform_type}")

            if transform_type == "filter":
                filter_preset = transform.get("params", {}).get("preset", "warm")
                vf = self._get_filter_string(filter_preset)
                video_filters.append(vf)
                transforms_applied.append(f"filter:{filter_preset}")

            elif transform_type == "duration_adjust":
                variance = job_data.get("duration_variance_percent", 20)
                factor = 1 + random.uniform(-variance/100, variance/100)
                speed_factor *= factor
                transforms_applied.append(f"duration:{factor:.2f}x")

            elif transform_type == "frame_shuffle":
                # 简化：添加轻微的帧率变化
                transforms_applied.append("frame_shuffle:simplified")

            elif transform_type == "sticker_overlay":
                # 添加贴纸叠加
                params = transform.get("params", {})

                # 支持随机选择贴纸
                sticker_id = params.get("sticker_id", None)
                if sticker_id is None:
                    # 默认使用随机贴纸，让 _get_sticker_filter 处理
                    sticker_id = "random"
                    print(f"[DEBUG] Using random sticker selection")

                # 位置控制 - 支持预设位置和自定义坐标
                position = params.get("position", "top_right")

                # 支持百分比坐标（优先）或像素坐标
                x_percent = params.get("x_percent", None)
                y_percent = params.get("y_percent", None)

                if x_percent is not None and y_percent is not None:
                    # 使用百分比坐标，根据视频分辨率转换为像素
                    video_width = video_info.get("width", 1080)
                    video_height = video_info.get("height", 1920)
                    x_offset = int((x_percent / 100) * video_width)
                    y_offset = int((y_percent / 100) * video_height)
                    print(f"[DEBUG] Converted percent ({x_percent}%, {y_percent}%) to pixels ({x_offset}, {y_offset}) for {video_width}x{video_height}")
                else:
                    # 使用像素坐标
                    x_offset = params.get("x", params.get("x_offset", 0))
                    y_offset = params.get("y", params.get("y_offset", 0))

                # 大小控制 - 支持自定义大小
                size = params.get("size", None)
                if size is None:
                    # 如果没有指定大小，使用默认值
                    size = 80 if position != "custom" else 100

                # 时间控制
                start_time = params.get("start_time", 0)
                end_time = params.get("end_time", -1)

                # 自定义图片路径
                sticker_image_path = params.get("image_path", None)

                # 自定义文字内容
                custom_text = params.get("text", None)

                sticker_filter = self._get_sticker_filter(
                    sticker_id, position, variant_index,
                    start_time=start_time, end_time=end_time, font_size=size,
                    x_offset=x_offset, y_offset=y_offset,
                    sticker_image_path=sticker_image_path,
                    custom_text=custom_text,
                    temp_dir=temp_dir
                )
                if sticker_filter:
                    video_filters.append(sticker_filter)
                    transforms_applied.append(f"sticker:{sticker_id}@{position}")

        # 应用速度调整
        if speed_factor != 1.0:
            video_filters.append(f"setpts={1/speed_factor}*PTS")
            if speed_factor <= 2.0:  # atempo 限制在 0.5-2.0
                audio_filters.append(f"atempo={speed_factor}")

        # 构建输出文件
        output_file = os.path.join(temp_dir, f"variant_{variant_index}.mp4")

        # 检查是否需要分片处理（长视频 > 120秒）
        duration = video_info.get("duration", 0)
        use_segmented = duration > 120 and len(video_filters) > 0

        if use_segmented:
            # 垂直分片处理：切片 -> 并行处理 -> 合并
            print(f"[INFO] Using segmented processing for {duration:.1f}s video")
            self._process_with_segments(
                source_path, output_file, video_filters, audio_filters, temp_dir, variant_index
            )
        else:
            # 短视频直接处理
            print(f"[DEBUG] Applying all transforms in one pass")
            self._apply_transforms_optimized(source_path, output_file, video_filters, audio_filters)

        print(f"[DEBUG] All transforms completed")

        current_file = output_file

        # 如果没有应用任何变换，复制原文件
        if current_file == source_path:
            output_file = os.path.join(temp_dir, f"variant_{variant_index}_copy.mp4")
            subprocess.run(["cp", source_path, output_file], check=True)
            current_file = output_file

        # 字幕生成（可选功能，带超时保护）
        enable_subtitle = job_data.get("enable_subtitle", False)
        if enable_subtitle:
            print(f"[INFO] Generating subtitle for variant {variant_index}")
            subtitle_language = job_data.get("subtitle_language", None)
            ass_path = os.path.join(temp_dir, f"subtitle_{variant_index}.ass")

            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(SubtitleGenerator.generate_subtitle, current_file, ass_path, subtitle_language)
                    subtitle_ok = future.result(timeout=300)  # 5 分钟超时

                if subtitle_ok:
                    # 烧录字幕到视频
                    subtitled_file = os.path.join(temp_dir, f"variant_{variant_index}_subtitled.mp4")
                    self._burn_subtitle(current_file, ass_path, subtitled_file)
                    current_file = subtitled_file
                    transforms_applied.append("subtitle:auto")
                    print(f"[INFO] Subtitle burned into video")
            except concurrent.futures.TimeoutError:
                print(f"[WARN] Subtitle generation timed out for variant {variant_index}, skipping subtitle")
            except Exception as sub_err:
                print(f"[WARN] Subtitle generation failed for variant {variant_index}: {sub_err}, skipping subtitle")

        # 检查文件大小
        file_size = os.path.getsize(current_file)
        max_size = job_data.get("max_output_size_mb", 500) * 1024 * 1024

        if file_size > max_size:
            compressed_file = os.path.join(temp_dir, f"variant_{variant_index}_compressed.mp4")
            self._compress_video(current_file, compressed_file, max_size)
            current_file = compressed_file
            file_size = os.path.getsize(current_file)

        # 上传到GCS
        drama_name = job_data["drama_name"]
        output_gcs_path = f"gs://{self.output_bucket}/fission/{drama_name}/{self.job_id}/variant_{variant_index}.mp4"
        self._upload_to_gcs(current_file, output_gcs_path)

        # 生成缩略图
        thumbnail_path = self._generate_thumbnail(current_file, temp_dir, variant_index)
        thumbnail_gcs_path = f"gs://{self.output_bucket}/fission/{drama_name}/{self.job_id}/variant_{variant_index}_thumb.jpg"
        self._upload_to_gcs(thumbnail_path, thumbnail_gcs_path)

        # 获取最终视频信息
        final_info = self._get_video_info(current_file)

        # 清理本地临时文件释放 tmpfs 内存
        variant_temp_files = [
            os.path.join(temp_dir, f"variant_{variant_index}.mp4"),
            os.path.join(temp_dir, f"variant_{variant_index}_copy.mp4"),
            os.path.join(temp_dir, f"variant_{variant_index}_subtitled.mp4"),
            os.path.join(temp_dir, f"variant_{variant_index}_compressed.mp4"),
            os.path.join(temp_dir, f"subtitle_{variant_index}.ass"),
            thumbnail_path,
        ]
        for tmp_file in variant_temp_files:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass

        import gc
        gc.collect()

        return {
            "variant_id": f"variant_{variant_index}",
            "output_path": output_gcs_path,
            "file_size_bytes": file_size,
            "duration_seconds": final_info["duration"],
            "transforms_applied": transforms_applied,
            "thumbnail_path": thumbnail_gcs_path
        }

    def _get_filter_string(self, preset: str) -> str:
        """获取滤镜字符串"""
        filter_map = {
            "warm": "colorbalance=rs=0.1:gs=0.05:bs=-0.1",
            "cool": "colorbalance=rs=-0.1:gs=0:bs=0.1",
            "vintage": "curves=vintage",
            "high_contrast": "eq=contrast=1.3:brightness=0.05",
            "soft": "gblur=sigma=0.5,eq=brightness=0.05"
        }
        return filter_map.get(preset, filter_map["warm"])

    def _get_random_sticker_id(self, category: str = None) -> str:
        """
        随机选择一个贴纸ID

        Args:
            category: 贴纸类别 (emoji, decoration, shapes, effects, badges, text)
                     如果为 None，则从所有类别中随机选择

        Returns:
            随机选择的贴纸ID
        """
        # 按类别分组的贴纸ID
        sticker_categories = {
            "emoji": [
                "sticker_fire", "sticker_heart", "sticker_laugh", "sticker_love",
                "sticker_cool", "sticker_cry", "sticker_shock", "sticker_party",
                "sticker_thumbsup", "sticker_clap", "sticker_muscle"
            ],
            "decoration": [
                "sticker_star", "sticker_sparkle", "sticker_crown", "sticker_diamond",
                "sticker_lightning", "sticker_explosion", "sticker_confetti", "sticker_balloon"
            ],
            "shapes": [
                "sticker_arrow_up", "sticker_arrow_down", "sticker_arrow_right",
                "sticker_circle", "sticker_square", "sticker_triangle",
                "sticker_check", "sticker_cross"
            ],
            "effects": [
                "sticker_glow", "sticker_shine", "sticker_shadow",
                "sticker_bubble", "sticker_smoke"
            ],
            "badges": [
                "sticker_hot_badge", "sticker_new_badge", "sticker_sale_badge",
                "sticker_vip_badge", "sticker_top_badge"
            ],
            "text": [
                "emoji_fire", "emoji_heart", "meme_666", "meme_yyds",
                "tag_hot", "tag_new", "tag_sale"
            ]
        }

        if category and category in sticker_categories:
            # 从指定类别中随机选择
            return random.choice(sticker_categories[category])
        else:
            # 从所有类别中随机选择
            all_stickers = []
            for stickers in sticker_categories.values():
                all_stickers.extend(stickers)
            return random.choice(all_stickers)

    def _get_sticker_filter(
        self,
        sticker_id: str,
        position: str,
        variant_index: int,
        start_time: float = 0,
        end_time: float = -1,
        x_offset: int = 0,
        y_offset: int = 0,
        font_size: int = 32,
        sticker_image_path: str = None,
        custom_text: str = None,
        temp_dir: str = None
    ) -> str:
        """
        生成贴纸滤镜字符串 - 支持 GCS 贴纸

        Args:
            sticker_id: 贴纸ID（从 GCS manifest 获取）或 "random"
            position: 位置 (top_left, top_right, bottom_left, bottom_right, custom)
            variant_index: 变体索引
            start_time: 贴纸开始显示时间（秒）
            end_time: 贴纸结束显示时间（秒），-1表示到视频结束
            x_offset: X轴偏移（像素）
            y_offset: Y轴偏移（像素）
            font_size: 字体大小（像素）
            sticker_image_path: 自定义图片路径（GCS 或本地）
            custom_text: 自定义文字
            temp_dir: 临时目录
        """
        # 贴纸位置配置
        positions = {
            "top_left": {"x": 20, "y": 20},
            "top_right": {"x": -120, "y": 20},
            "bottom_left": {"x": 20, "y": -180},
            "bottom_right": {"x": -120, "y": -180},
            "center": {"x": "(w-overlay_w)/2", "y": "(h-overlay_h)/2"},
            "custom": {"x": x_offset, "y": y_offset},
        }

        pos = positions.get(position, positions["top_right"])

        # 获取贴纸信息
        sticker_info = None
        local_sticker_path = None

        if sticker_id == "custom_image" and sticker_image_path:
            # 自定义图片贴纸
            if sticker_image_path.startswith("gs://") and temp_dir:
                local_sticker_path = self._download_sticker_from_gcs(sticker_image_path, temp_dir)
            elif sticker_image_path.startswith("/stickers/") and temp_dir:
                # 前端传递的 /stickers/ 路径，需要从 GCS 下载
                local_sticker_path = self._download_sticker_from_gcs(sticker_image_path, temp_dir)
            else:
                local_sticker_path = sticker_image_path
            # 根据文件扩展名判断类型
            sticker_type = "gif" if sticker_image_path.lower().endswith(".gif") else "image"
            sticker_info = {"type": sticker_type, "size": font_size}

        elif sticker_id == "custom_text":
            # 自定义文字贴纸
            sticker_info = {"type": "text", "text": custom_text or "TEXT", "size": font_size}

        elif sticker_id == "random" and temp_dir:
            # 随机选择贴纸
            gcs_sticker = self._get_random_sticker_from_gcs(None, temp_dir)
            if gcs_sticker:
                local_sticker_path = gcs_sticker["local_path"]
                sticker_info = {"type": gcs_sticker["type"], "size": gcs_sticker["size"]}

        elif temp_dir:
            # 从 GCS manifest 获取贴纸
            gcs_sticker = self._get_sticker_from_manifest(sticker_id, temp_dir)
            if gcs_sticker:
                local_sticker_path = gcs_sticker["local_path"]
                sticker_info = {"type": gcs_sticker["type"], "size": gcs_sticker["size"]}

        if not sticker_info:
            print(f"[WARNING] Sticker not found: {sticker_id}")
            return None

        # 计算坐标表达式
        x_val = pos["x"]
        y_val = pos["y"]

        if x_val < 0:
            x_expr = f"(w{x_val})"
        else:
            x_expr = str(x_val)

        if y_val < 0:
            y_expr = f"(h{y_val})"
        else:
            y_expr = str(y_val)

        # 构建时间控制表达式
        if end_time > 0:
            enable_expr = f"between(t\\,{start_time}\\,{end_time})"
        elif start_time > 0:
            enable_expr = f"gte(t\\,{start_time})"
        else:
            enable_expr = "1"

        # 判断贴纸类型
        sticker_type = sticker_info.get("type", "text")
        sticker_size = sticker_info.get("size", font_size)

        if sticker_type in ("image", "gif") and local_sticker_path:
            # 图片/GIF 贴纸
            filter_str = f"image|{local_sticker_path}|{x_expr}|{y_expr}|{sticker_size}|{enable_expr}"

        elif sticker_type == "text":
            # 文字贴纸
            text = sticker_info.get("text", custom_text or "TEXT")
            box_padding = max(8, sticker_size // 4)
            filter_str = (
                f"drawtext=text='{text}':"
                f"fontsize={sticker_size}:"
                f"fontcolor=white:"
                f"x={x_expr}:y={y_expr}:"
                f"box=1:boxcolor=black@0.7:boxborderw={box_padding}:"
                f"enable='{enable_expr}'"
            )

        else:
            print(f"[WARNING] Unknown sticker type: {sticker_type}")
            return None

        print(f"[DEBUG] Sticker filter: {filter_str}")
        return filter_str

    def _build_filter_complex(
        self,
        normal_filters: List[str],
        image_stickers: List[Dict[str, Any]],
        audio_filters: List[str]
    ) -> str:
        """
        构建 ffmpeg filter_complex 字符串，支持图片和 GIF 贴纸叠加

        Args:
            normal_filters: 普通视频滤镜列表
            image_stickers: 图片/GIF 贴纸配置列表
            audio_filters: 音频滤镜列表

        Returns:
            filter_complex 字符串
        """
        filter_parts = []

        # 第一步：对主视频应用普通滤镜
        if normal_filters:
            vf_chain = ",".join(normal_filters)
            filter_parts.append(f"[0:v]{vf_chain}[v0]")
            current_video = "[v0]"
        else:
            current_video = "[0:v]"

        # 第二步：依次叠加每个贴纸
        for i, sticker in enumerate(image_stickers):
            input_idx = i + 1  # 贴纸输入从 1 开始（0 是主视频）
            sticker_path = sticker["path"]
            x_expr = sticker["x"]
            y_expr = sticker["y"]
            size = sticker["size"]
            enable = sticker["enable"]

            # 检查是否是 GIF
            is_gif = sticker_path.lower().endswith(".gif")

            # 缩放贴纸到指定大小
            scale_filter = f"[{input_idx}:v]scale={size}:{size}:force_original_aspect_ratio=decrease"

            if is_gif:
                # GIF 需要添加 format 确保有 alpha 通道
                scale_filter += ",format=rgba"

            scale_filter += f"[sticker{i}]"
            filter_parts.append(scale_filter)

            # 叠加贴纸到视频上
            # 处理坐标表达式中的括号
            x_pos = x_expr.replace("(", "").replace(")", "") if "(" in x_expr else x_expr
            y_pos = y_expr.replace("(", "").replace(")", "") if "(" in y_expr else y_expr

            # 构建 overlay 滤镜
            if is_gif:
                # GIF 使用 shortest=1 确保 GIF 循环直到视频结束
                overlay = f"{current_video}[sticker{i}]overlay={x_pos}:{y_pos}"
                overlay += f":enable='{enable}':shortest=0:eof_action=repeat"
            else:
                # 静态图片
                overlay = f"{current_video}[sticker{i}]overlay={x_pos}:{y_pos}"
                overlay += f":enable='{enable}'"

            # 输出标签
            if i < len(image_stickers) - 1:
                overlay += f"[v{i+1}]"
                current_video = f"[v{i+1}]"
            else:
                overlay += "[vout]"

            filter_parts.append(overlay)

        # 如果没有贴纸但有普通滤镜，需要重命名输出
        if not image_stickers and normal_filters:
            # 修改最后一个滤镜的输出标签
            if filter_parts:
                filter_parts[-1] = filter_parts[-1].replace("[v0]", "[vout]")
            else:
                filter_parts.append(f"[0:v]null[vout]")
        elif not image_stickers and not normal_filters:
            filter_parts.append("[0:v]null[vout]")

        return ";".join(filter_parts)

    def _apply_transforms_optimized(
        self,
        input_path: str,
        output_path: str,
        video_filters: List[str],
        audio_filters: List[str]
    ) -> None:
        """一次性应用所有变换 - 性能优化，支持图片/GIF贴纸"""
        # 分离图片贴纸滤镜和普通滤镜
        image_stickers = []
        normal_filters = []

        for vf in video_filters:
            if vf.startswith("image|"):
                # 解析图片贴纸: image|路径|x|y|size|enable
                parts = vf.split("|")
                if len(parts) >= 6:
                    image_stickers.append({
                        "path": parts[1],
                        "x": parts[2],
                        "y": parts[3],
                        "size": int(parts[4]),
                        "enable": parts[5]
                    })
            else:
                normal_filters.append(vf)

        cmd = ["ffmpeg", "-i", input_path]

        # 如果有图片/GIF贴纸，使用 filter_complex
        if image_stickers:
            # 添加所有贴纸输入
            for i, sticker in enumerate(image_stickers):
                # 检查是否是 GIF
                is_gif = sticker["path"].lower().endswith(".gif")
                if is_gif:
                    # GIF: -ignore_loop 0 循环播放, -r 10 限制帧率减少解码压力
                    cmd.extend(["-ignore_loop", "0", "-r", "10", "-i", sticker["path"]])
                else:
                    cmd.extend(["-i", sticker["path"]])

            # 构建 filter_complex
            filter_complex = self._build_filter_complex(
                normal_filters, image_stickers, audio_filters
            )
            cmd.extend(["-filter_complex", filter_complex])
            cmd.extend(["-map", "[vout]", "-map", "0:a?"])
            print(f"[DEBUG] Filter complex: {filter_complex}")
        else:
            # 没有图片贴纸，使用简单的 -vf
            if normal_filters:
                vf_chain = ",".join(normal_filters)
                cmd.extend(["-vf", vf_chain])
                print(f"[DEBUG] Video filter chain: {vf_chain}")

        # 添加音频滤镜
        if audio_filters:
            af_chain = ",".join(audio_filters)
            cmd.extend(["-af", af_chain])
            print(f"[DEBUG] Audio filter chain: {af_chain}")

        # 编码参数优化 - 速度优先
        # 根据并发数分配线程，避免多个 ffmpeg 进程争抢 CPU
        cpu_count = os.cpu_count() or 4
        max_workers = int(os.environ.get("FISSION_PARALLEL_SEGMENTS", str(cpu_count)))
        threads_per_process = max(1, cpu_count // max_workers)
        cmd.extend([
            "-c:v", "libx264",           # 视频编码器
            "-preset", "ultrafast",       # 最快编码速度
            "-profile:v", "main",         # main profile（编码效率更高）
            "-level", "4.0",              # H.264 level 4.0（支持更高分辨率）
            "-crf", "28",                 # 质量参数（28 换取更快速度）
            "-threads", str(threads_per_process),  # 按并发数分配线程，避免争抢
            "-c:a", "aac",                # 音频编码器
            "-b:a", "128k",              # 音频比特率
            "-ar", "44100",               # 音频采样率
            "-strict", "experimental",    # 允许实验性编码器
            "-movflags", "+faststart",    # 优化流媒体播放
            "-pix_fmt", "yuv420p",        # 像素格式（兼容性最好）
            "-y",                         # 覆盖输出文件
            output_path
        ])

        print(f"[DEBUG] Running optimized ffmpeg command")
        print(f"[DEBUG] Command: {' '.join(cmd[:10])}...")  # 只打印前10个参数

        # 使用 Popen + 后台线程读取 stderr，避免 pipe buffer 满导致死锁
        import time
        import threading
        start_time = time.time()
        timeout_seconds = 600  # 10 分钟超时（长视频+GIF 贴纸处理较慢）

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )

        # 后台线程持续消费 stderr，防止 pipe buffer 写满导致 ffmpeg 阻塞
        stderr_chunks = []
        def _drain_stderr():
            try:
                for line in iter(process.stderr.readline, ''):
                    stderr_chunks.append(line)
            except ValueError:
                pass
            finally:
                process.stderr.close()

        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        # 等待进程完成，定期检查超时
        while process.poll() is None:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                process.kill()
                process.wait()
                raise Exception(f"FFmpeg timeout after {timeout_seconds}s")

            # 每 30 秒输出一次进度
            if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                print(f"[INFO] FFmpeg processing... {int(elapsed)}s elapsed")

            time.sleep(1)

        stderr_thread.join(timeout=5)
        stderr = "".join(stderr_chunks)
        elapsed = time.time() - start_time

        if process.returncode != 0:
            print(f"[ERROR] ffmpeg failed after {elapsed:.1f}s: {stderr[-500:]}")
            raise Exception(f"ffmpeg failed: {stderr[-500:]}")

        print(f"[DEBUG] Transform completed in {elapsed:.1f}s")

    def _apply_filter(self, input_path: str, output_path: str, preset: str) -> None:
        """应用滤镜（已废弃，保留用于兼容）"""
        vf = self._get_filter_string(preset)
        cmd = ["ffmpeg", "-i", input_path, "-vf", vf, "-y", output_path]
        subprocess.run(cmd, check=True, capture_output=True)

    def _adjust_duration(self, input_path: str, output_path: str, variance: int, video_info: Dict) -> float:
        """调整视频时长"""
        original_duration = video_info.get("duration", 60)
        # 随机调整 ±variance%
        factor = 1 + random.uniform(-variance/100, variance/100)
        new_duration = original_duration * factor

        # 使用 setpts 调整速度
        speed = original_duration / new_duration
        vf = f"setpts={1/speed}*PTS"
        af = f"atempo={speed}"

        cmd = ["ffmpeg", "-i", input_path, "-vf", vf, "-af", af, "-y", output_path]
        subprocess.run(cmd, check=True, capture_output=True)
        return new_duration

    def _frame_shuffle(self, input_path: str, output_path: str, intensity: float) -> None:
        """抽帧重组（简化版：随机裁剪片段重组）"""
        # 简化实现：添加随机效果
        # 实际生产中应该更复杂
        cmd = [
            "ffmpeg", "-i", input_path,
            "-vf", f"random=frames={int(intensity * 10)}:seed={random.randint(1,1000)}",
            "-y", output_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except:
            # 如果 random 滤镜不支持，直接复制
            subprocess.run(["ffmpeg", "-i", input_path, "-c", "copy", "-y", output_path], check=True)

    def _burn_subtitle(self, input_path: str, ass_path: str, output_path: str) -> None:
        """将 ASS 字幕烧录到视频中"""
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"ass={ass_path}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-c:a", "copy",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] Burn subtitle failed: {result.stderr[-300:]}")
            raise Exception(f"Burn subtitle failed")

    def _compress_video(self, input_path: str, output_path: str, target_size: int) -> None:
        """压缩视频到目标大小"""
        import subprocess
        
        # 简单的压缩策略：降低比特率
        cmd = [
            "ffmpeg", "-i", input_path,
            "-b:v", "2M",  # 视频比特率
            "-b:a", "128k",  # 音频比特率
            "-y", output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _generate_thumbnail(self, video_path: str, temp_dir: str, variant_index: int) -> str:
        """生成缩略图"""
        import subprocess
        
        thumbnail_path = os.path.join(temp_dir, f"thumbnail_{variant_index}.jpg")
        cmd = [
            "ffmpeg", "-i", video_path,
            "-ss", "00:00:01",  # 取第1秒的帧
            "-vframes", "1",
            "-y", thumbnail_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return thumbnail_path

    def _add_variant_to_job(self, variant: Dict[str, Any]) -> None:
        """原子操作：将变体添加到任务（支持并行）"""
        self.job_ref.update({
            "variants": firestore.ArrayUnion([variant]),
            "updated_at": SERVER_TIMESTAMP,
        })
        print(f"[INFO] Variant {variant['variant_id']} added to job")

    def _update_task_error(self, task_index: int, error_msg: str) -> None:
        """记录任务错误"""
        self.job_ref.update({
            "status": "FAILED",
            "error_message": error_msg,
            f"task_errors.task_{task_index}": error_msg,
            "updated_at": SERVER_TIMESTAMP,
        })

    def _update_segment_progress(self, variant_index: int, completed_segments: int, total_segments: int) -> None:
        """更新分片级进度"""
        try:
            variant_count = getattr(self, 'variant_count', 1)
            job_doc = self.job_ref.get()
            if job_doc.exists:
                completed_variants = len(job_doc.to_dict().get("variants", []))
            else:
                completed_variants = 0
            # 总进度 = (已完成变体 * 总片段数 + 当前变体已完成片段) / (总变体数 * 总片段数)
            total_work = variant_count * total_segments
            done_work = completed_variants * total_segments + completed_segments
            progress = int(done_work / total_work * 100)
            progress = min(progress, 99)  # 留给 _update_progress 设置最终值
            self.job_ref.update({
                "progress": progress,
                "progress_text": f"Processing segment {completed_segments}/{total_segments} (变体 {variant_index+1}/{variant_count})",
                "updated_at": SERVER_TIMESTAMP,
            })
            print(f"[INFO] Segment progress: {progress}% (variant {variant_index}, segment {completed_segments}/{total_segments})")
        except Exception as e:
            print(f"[WARNING] Failed to update segment progress: {e}")

    def _update_progress(self) -> None:
        """更新任务进度（基于已完成的变体数量）"""
        try:
            job_doc = self.job_ref.get()
            if job_doc.exists:
                job_data = job_doc.to_dict()
                variant_count = job_data.get("variant_count", 0)
                completed_variants = len(job_data.get("variants", []))

                if variant_count > 0:
                    progress = int((completed_variants / variant_count) * 100)
                    self.job_ref.update({
                        "progress": progress,
                        "progress_text": f"已完成 {completed_variants}/{variant_count} 个变体",
                        "updated_at": SERVER_TIMESTAMP,
                    })
                    print(f"[INFO] Progress updated: {progress}% ({completed_variants}/{variant_count})")
        except Exception as e:
            print(f"[WARNING] Failed to update progress: {e}")

    def _check_and_complete_job(self, expected_variant_count: int) -> None:
        """检查是否所有变体都完成了，如果是则更新任务状态为 COMPLETED"""
        try:
            job_doc = self.job_ref.get()
            if job_doc.exists:
                job_data = job_doc.to_dict()
                completed_variants = len(job_data.get("variants", []))

                if completed_variants >= expected_variant_count:
                    self.job_ref.update({
                        "status": "COMPLETED",
                        "progress": 100,
                        "progress_text": f"全部完成！共生成 {completed_variants} 个变体",
                        "updated_at": SERVER_TIMESTAMP,
                    })
                    print(f"[INFO] Job completed! All {completed_variants} variants generated.")
        except Exception as e:
            print(f"[WARNING] Failed to check job completion: {e}")

    def _update_status(
        self,
        status: str,
        progress: int,
        progress_text: str,
        variants: List[Dict[str, Any]] = None
    ) -> None:
        """更新任务状态"""
        update_data = {
            "status": status,
            "progress": progress,
            "progress_text": progress_text,
            "updated_at": SERVER_TIMESTAMP,
        }

        if status == "FAILED":
            update_data["error_message"] = progress_text

        if variants:
            update_data["variants"] = variants

        self.job_ref.update(update_data)


def main():
    """Worker入口 - 支持并行分片"""
    # Cloud Run Jobs 会自动设置这些环境变量
    task_index = int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0"))
    task_count = int(os.environ.get("CLOUD_RUN_TASK_COUNT", "1"))

    if len(sys.argv) < 2:
        print("Usage: python main.py <job_id>")
        sys.exit(1)

    job_id = sys.argv[1]

    print(f"[INFO] Starting task {task_index}/{task_count} for job {job_id}")

    worker = FissionWorker(job_id)
    worker.process(task_index=task_index, task_count=task_count)


if __name__ == "__main__":
    main()

