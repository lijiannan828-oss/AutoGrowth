#!/usr/bin/env python3
"""Diagnose pairing issue by checking GCS file structure and simulating pairing logic.

Usage:
    python scripts/diagnose_pairing_issue.py --drama-name "US044P01S01_Runaway Prince's Secret Vacation"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from google.cloud import storage
from app.core.config import settings
from app.core.firestore import get_firestore_client, init_firestore
from app.workers.process.main import (
    extract_episode,
    detect_language,
    _looks_like_language_folder,
)


def list_gcs_files(drama_name: str, bucket_name: str) -> List[Dict[str, str]]:
    """List all files in GCS for a given drama."""
    import os
    from google.oauth2 import service_account
    
    # Try to load credentials from service account file
    creds_path = settings.google_application_credentials
    if creds_path and os.path.exists(creds_path):
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        client = storage.Client(credentials=credentials, project=settings.firestore_project_id)
    else:
        client = storage.Client(project=settings.firestore_project_id)
    
    bucket = client.bucket(bucket_name)
    
    prefix = f"{drama_name}/"
    blobs = list(client.list_blobs(bucket_name, prefix=prefix))
    
    files = []
    for blob in blobs:
        rel_path = blob.name[len(prefix):] if blob.name.startswith(prefix) else blob.name
        files.append({
            "full_path": blob.name,
            "relative_path": rel_path,
            "name": blob.name.split("/")[-1],
            "size": blob.size or 0,
        })
    
    return sorted(files, key=lambda x: x["relative_path"])


def simulate_pairing(drama_name: str, bucket_name: str):
    """Simulate the pairing logic to see what's happening."""
    print("=" * 80)
    print("🔍 配对逻辑诊断")
    print("=" * 80)
    print(f"\nDrama Name: {drama_name}")
    print(f"Bucket: {bucket_name}")
    
    # List all files
    print("\n" + "=" * 80)
    print("步骤 1: 列出 GCS 中的所有文件")
    print("=" * 80)
    files = list_gcs_files(drama_name, bucket_name)
    
    if not files:
        print(f"❌ 未找到任何文件")
        return
    
    print(f"✅ 找到 {len(files)} 个文件\n")
    
    videos: Dict[str, Dict] = {}
    subtitles: Dict[str, Dict[str, Dict]] = {}
    
    # Process each file
    print("=" * 80)
    print("步骤 2: 处理文件并分类")
    print("=" * 80)
    
    for file_info in files:
        rel_path = file_info["relative_path"]
        lower = rel_path.lower()
        filename = Path(rel_path).name.lower()
        
        # Use the same logic as _register_media_blob (fixed version)
        is_video = False
        if ".mp4" in filename:
            mp4_idx = filename.find(".mp4")
            if mp4_idx >= 0:
                after_mp4 = filename[mp4_idx + 4:]
                if not after_mp4:
                    is_video = True
                elif "." not in after_mp4[:20]:
                    is_video = True
        
        if is_video:
            episode = extract_episode(rel_path)
            if episode:
                videos[episode] = {
                    "episode": episode,
                    "path": rel_path,
                    "full_path": file_info["full_path"],
                }
                print(f"✅ 视频: EP{episode} -> {rel_path}")
            else:
                print(f"⚠️  视频（无法提取集数）: {rel_path}")
        
        elif lower.endswith(".srt"):
            episode = extract_episode(rel_path)
            if not episode:
                print(f"⚠️  字幕（无法提取集数）: {rel_path}")
                continue
            
            language = detect_language(rel_path)
            if language == "unknown":
                print(f"⚠️  字幕（无法识别语言）: {rel_path}")
                print(f"   路径部分: {rel_path.split('/')}")
            
            subtitles.setdefault(language, {})[episode] = {
                "episode": episode,
                "language": language,
                "path": rel_path,
                "full_path": file_info["full_path"],
            }
            print(f"✅ 字幕: EP{episode} | Lang: {language} -> {rel_path}")
    
    # Summary
    print("\n" + "=" * 80)
    print("步骤 3: 配对结果")
    print("=" * 80)
    
    print(f"\n📹 找到的视频文件: {len(videos)} 个")
    for episode, video_info in sorted(videos.items()):
        print(f"   EP{episode}: {video_info['path']}")
    
    print(f"\n📝 找到的字幕文件: {sum(len(episodes) for episodes in subtitles.values())} 个")
    for language, episodes in sorted(subtitles.items()):
        print(f"   语言 {language}: {len(episodes)} 个")
        for episode, sub_info in sorted(episodes.items()):
            print(f"      EP{episode}: {sub_info['path']}")
    
    # Find pairs
    print("\n" + "=" * 80)
    print("步骤 4: 查找配对")
    print("=" * 80)
    
    pairs = []
    for language, episodes in subtitles.items():
        for episode, sub_info in episodes.items():
            video_info = videos.get(episode)
            if video_info:
                pairs.append({
                    "episode": episode,
                    "language": language,
                    "video": video_info["path"],
                    "subtitle": sub_info["path"],
                })
                print(f"✅ 配对: EP{episode} | Lang: {language}")
                print(f"   视频: {video_info['path']}")
                print(f"   字幕: {sub_info['path']}")
            else:
                print(f"❌ 未配对: EP{episode} | Lang: {language} (缺少视频)")
                print(f"   字幕: {sub_info['path']}")
    
    # Check unmatched videos
    print("\n" + "=" * 80)
    print("步骤 5: 未配对的视频")
    print("=" * 80)
    
    matched_episodes = {pair["episode"] for pair in pairs}
    unmatched_videos = {ep: info for ep, info in videos.items() if ep not in matched_episodes}
    
    if unmatched_videos:
        print(f"⚠️  找到 {len(unmatched_videos)} 个未配对的视频:")
        for episode, video_info in sorted(unmatched_videos.items()):
            print(f"   EP{episode}: {video_info['path']}")
    else:
        print("✅ 所有视频都已配对")
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 诊断总结")
    print("=" * 80)
    
    print(f"\n总文件数: {len(files)}")
    print(f"视频文件: {len(videos)}")
    print(f"字幕文件: {sum(len(episodes) for episodes in subtitles.values())}")
    print(f"成功配对: {len(pairs)}")
    
    if len(pairs) == 0:
        print("\n❌ 问题：没有找到任何配对")
        print("\n可能的原因：")
        print("1. 视频和字幕的集数提取不匹配")
        print("2. 语言识别失败（detect_language 返回 'unknown'）")
        print("3. 文件路径结构不符合预期")
        print("\n建议检查：")
        print("- 视频文件路径是否包含 'episodes/final/'")
        print("- 字幕文件路径是否包含 'subtitles/final/<language>/'")
        print("- 文件名是否包含集数（如 ep001, ep002）")
    else:
        print(f"\n✅ 找到 {len(pairs)} 个配对，应该可以正常处理")


def main():
    parser = argparse.ArgumentParser(description="Diagnose pairing issue")
    parser.add_argument("--drama-name", required=True, help="Drama name")
    parser.add_argument("--bucket", default="vigloo_source", help="GCS bucket name")
    args = parser.parse_args()
    
    simulate_pairing(args.drama_name, args.bucket)
    return 0


if __name__ == "__main__":
    sys.exit(main())

