#!/usr/bin/env python3
"""
Utility script to validate subtitle styling for a single language/episode pair.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from google.cloud import storage

from app.core.config import settings
from app.workers.process.main import (
    build_subtitle_style,
    detect_fonts_dir,
    detect_language,
    download_with_progress,
    ensure_ffmpeg,
    extract_episode,
    get_default_font_name,
    normalize_language_key,
    normalize_subtitle_encoding,
)


def _log(message: str) -> None:
    print(f"[style-validation] {message}", flush=True)


def _parse_gs_uri(uri: str) -> Tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"无效的 GCS URI: {uri}")
    path = uri[5:]
    parts = path.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"无效的 GCS URI: {uri}")
    return parts[0], parts[1]


def _auto_select_pair(
    storage_client: storage.Client,
    source_bucket: str,
    drama_name: str,
    language: str,
    episode: str | None,
) -> Tuple[storage.Blob, storage.Blob, str]:
    prefix = drama_name.strip("/")
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"

    target_exact = language.strip().lower()
    target_norm = normalize_language_key(language)

    videos: dict[str, storage.Blob] = {}
    subtitles: dict[str, Tuple[storage.Blob, str]] = {}

    for blob in storage_client.list_blobs(source_bucket, prefix=prefix):
        rel_path = blob.name[len(prefix) :] if prefix else blob.name
        rel_path = rel_path.lstrip("/")
        if not rel_path:
            continue
        lower = rel_path.lower()
        if lower.endswith(".mp4"):
            episode_id = extract_episode(rel_path)
            if episode_id:
                videos[episode_id] = blob
        elif lower.endswith(".srt"):
            episode_id = extract_episode(rel_path)
            if not episode_id:
                continue
            if episode and episode_id != episode:
                continue
            detected = detect_language(rel_path)
            detected_exact = detected.lower()
            detected_norm = normalize_language_key(detected)
            matches = detected_exact == target_exact
            if not matches and "_" not in target_exact and "-" not in target_exact:
                matches = target_norm and detected_norm == target_norm
            if not matches:
                continue
            subtitles[episode_id] = (blob, detected)

    candidates = sorted(subtitles.items(), key=lambda item: item[0])
    for episode_id, (subtitle_blob, detected_language) in candidates:
        video_blob = videos.get(episode_id)
        if not video_blob:
            continue
        _log(
            f"🔍 Found pair for episode {episode_id}: "
            f"language={detected_language}, subtitle={subtitle_blob.name}"
        )
        return video_blob, subtitle_blob, episode_id

    raise RuntimeError(
        f"未在 {source_bucket}/{drama_name} 中找到语言 {language} 的可用配对"
    )


def _prepare_blob(
    storage_client: storage.Client,
    uri: str,
) -> storage.Blob:
    bucket_name, object_name = _parse_gs_uri(uri)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.reload()
    return blob


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate subtitle styling for a single pair.")
    parser.add_argument("--drama-name", required=True, help="剧集名称（与 GCS 路径一致）")
    parser.add_argument("--language", required=True, help="语言标识，如 ko 或 ja_translated")
    parser.add_argument("--episode", help="可选，目标集（如 001）")
    parser.add_argument("--video", help="可选，显式指定 gs://...mp4")
    parser.add_argument("--subtitle", help="可选，显式指定 gs://...srt")
    parser.add_argument(
        "--source-bucket",
        default=settings.pipeline_gcs_source_bucket,
        help="源文件 GCS 桶名称",
    )
    parser.add_argument(
        "--processed-bucket",
        default=settings.pipeline_gcs_processed_bucket,
        help="压制结果存储的 GCS 桶",
    )
    parser.add_argument(
        "--output-prefix",
        default="style_previews",
        help="压制结果在目标桶下的子目录",
    )
    args = parser.parse_args()

    if (args.video and not args.subtitle) or (args.subtitle and not args.video):
        parser.error("video 和 subtitle 需要同时提供，或者都留空由脚本自动匹配。")

    if not settings.google_application_credentials:
        parser.error("请先设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量。")

    ensure_ffmpeg()

    storage_client = storage.Client()

    if args.video:
        video_blob = _prepare_blob(storage_client, args.video)
        subtitle_blob = _prepare_blob(storage_client, args.subtitle)
        _, video_object = _parse_gs_uri(args.video)
        episode = args.episode or extract_episode(Path(video_object).name) or "demo"
    else:
        video_blob, subtitle_blob, episode = _auto_select_pair(
            storage_client,
            args.source_bucket,
            args.drama_name,
            args.language,
            args.episode,
        )

    fonts_dir = detect_fonts_dir()
    default_font = get_default_font_name()
    style, font_used = build_subtitle_style(args.language, default_font)

    safe_lang = args.language.replace("/", "_")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_blob_path = (
        f"{args.drama_name.strip('/')}/{args.output_prefix.strip('/')}/"
        f"{safe_lang}/ep{episode}_{timestamp}.mp4"
    )

    processed_bucket = storage_client.bucket(args.processed_bucket)

    with tempfile.TemporaryDirectory(prefix="style-validation-") as tmpdir:
        temp_dir = Path(tmpdir)
        video_path = temp_dir / f"{safe_lang}_input_ep{episode}.mp4"
        subtitle_path = temp_dir / f"{safe_lang}_input_ep{episode}.srt"
        output_path = temp_dir / f"{safe_lang}_output_ep{episode}.mp4"

        download_with_progress(video_blob, video_path, f"{args.language} ep{episode} video")
        download_with_progress(subtitle_blob, subtitle_path, f"{args.language} ep{episode} subtitle")
        normalize_subtitle_encoding(subtitle_path)

        subtitle_size = subtitle_path.stat().st_size
        _log(f"🔍 Subtitle size {subtitle_path.name}: {subtitle_size} bytes")

        preview_lines = []
        with subtitle_path.open("r", encoding="utf-8", errors="ignore") as fh:
            for _ in range(10):
                line = fh.readline()
                if not line:
                    break
                preview_lines.append(line.rstrip("\n"))

        _log(f"🔤 使用字体 {font_used} (fontsdir={fonts_dir or 'system-default'})")

        vf_components = [f"subtitles={subtitle_path.name}"]
        if fonts_dir:
            vf_components.append(f"fontsdir={fonts_dir}")
        vf_components.append(f"force_style='{style}'")
        vf_arg = ":".join(vf_components)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path.name,
            "-vf",
            vf_arg,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-c:a",
            "copy",
            output_path.name,
        ]

        _log("🔍 字幕预览:")
        for line in preview_lines:
            _log(f"    {line}")
        _log("🔍 FFmpeg 命令:\n" + " ".join(cmd))

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(temp_dir),
        )
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            if not line.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.flush()
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"FFmpeg 处理失败 (exit={return_code})")

        processed_bucket.blob(output_blob_path).upload_from_filename(output_path)

    _log(f"✅ 压制完成：gs://{args.processed_bucket}/{output_blob_path}")


if __name__ == "__main__":
    main()

