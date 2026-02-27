"""Service for discovering video/subtitle pairs in GCS.

This service provides a shared utility for discovering file pairs,
ensuring consistent sorting and filtering logic between Service and Worker.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from google.cloud import storage

from app.core.config import settings

EPISODE_REGEX = re.compile(r"(?:ep|episode|e)?[-_\s]*(\d{1,3})", re.IGNORECASE)


@dataclass
class FilePairInfo:
    """Information about a video/subtitle pair (without blob objects)."""
    episode: str
    language: str
    video_path: str
    subtitle_path: str


def extract_episode(source: str) -> str | None:
    """Extract episode number from filename.

    Priority order:
    1. "episode" followed by a number (e.g., episode000)
    2. "ep" followed by a number (e.g., ep000)
    3. General fallback pattern
    """
    filename = Path(source).stem

    # Priority 1: "episode" + number
    m = re.search(r"episode[-_\s]*(\d{1,3})", filename, re.IGNORECASE)
    if m:
        return f"{int(m.group(1)):03d}"

    # Priority 2: "ep" + number
    m = re.search(r"ep[-_\s]*(\d{1,3})", filename, re.IGNORECASE)
    if m:
        return f"{int(m.group(1)):03d}"

    # Priority 3: General fallback
    m = EPISODE_REGEX.search(filename)
    if not m:
        return None
    return f"{int(m.group(1)):03d}"


def detect_language(relative_path: str) -> str:
    """Detect language from subtitle file path."""
    parts = [p for p in relative_path.split("/") if p]
    language = "unknown"
    anchor_idx: int | None = None

    for idx, part in enumerate(parts):
        if "subtitles" in part.lower():
            anchor_idx = idx
            break

    if anchor_idx is None:
        return language

    ignore_tokens = {"final", "ready", "completed", "output"}
    found = False
    for candidate in parts[anchor_idx + 1 :]:
        candidate_clean = candidate.strip()
        if not candidate_clean:
            continue
        if candidate_clean.lower() in ignore_tokens:
            continue
        if re.fullmatch(r"[A-Za-z0-9_\-]+", candidate_clean):
            language = candidate_clean.lower()
            found = True
            break

    if not found:
        match = re.search(r"(?:[_\.-]([a-zA-Z]{2,5}(?:-[A-Za-z0-9]+)?))$", relative_path)
        if match:
            language = match.group(1).lower()

    return language


def _is_video_file(filename: str) -> bool:
    """Check if a file is a video file.
    
    Supports common video formats:
    - MP4: .mp4, .m4v
    - QuickTime: .mov, .qt
    - AVI: .avi, .divx, .xvid
    - Matroska: .mkv, .mka, .mks
    - Windows Media: .wmv, .asf
    - Flash: .flv, .f4v
    - Web: .webm
    - MPEG: .mpg, .mpeg, .m2v, .mpe
    - Transport Stream: .ts, .mts, .m2ts
    - RealMedia: .rm, .rmvb
    - OGG: .ogv, .ogg
    - 3GP: .3gp, .3g2
    - VOB: .vob
    - Other: .vro, .amv, .nsv
    
    Also handles files with suffixes like ".mp4의 사본" or ".mov的副本"
    """
    lower = filename.lower()
    
    # Common video extensions
    video_extensions = [
        # MP4 family
        ".mp4", ".m4v",
        # QuickTime
        ".mov", ".qt",
        # AVI family
        ".avi", ".divx", ".xvid",
        # Matroska
        ".mkv", ".mka", ".mks",
        # Windows Media
        ".wmv", ".asf",
        # Flash
        ".flv", ".f4v",
        # Web
        ".webm",
        # MPEG
        ".mpg", ".mpeg", ".m2v", ".mpe",
        # Transport Stream
        ".ts", ".mts", ".m2ts",
        # RealMedia
        ".rm", ".rmvb",
        # OGG
        ".ogv", ".ogg",
        # 3GP
        ".3gp", ".3g2",
        # VOB
        ".vob",
        # Other
        ".vro", ".amv", ".nsv",
    ]
    
    # Check each video extension
    for ext in video_extensions:
        if ext in lower:
            ext_idx = lower.find(ext)
            if ext_idx >= 0:
                after_ext = lower[ext_idx + len(ext):]
                # If nothing after extension, or no other dot (indicating another extension) in the next 20 chars
                # This handles cases like ".mp4의 사본" or ".mov的副本"
                if not after_ext or "." not in after_ext[:20]:
                    return True
    
    return False


def discover_file_pairs(
    drama_name: str,
    source_bucket: str | None = None,
    allowed_languages: set[str] | None = None,
    max_pairs_per_language: int | None = None,
    max_pairs_total: int | None = None,
    allowed_paths: set[str] | None = None,
) -> List[FilePairInfo]:
    """Discover video/subtitle pairs in GCS.
    
    This function provides the same logic as Worker's _build_processing_pairs,
    but returns lightweight FilePairInfo objects instead of SubtitlePair with blobs.
    
    Args:
        drama_name: Drama name (used as GCS prefix)
        source_bucket: GCS bucket name (defaults to settings.pipeline_gcs_source_bucket)
        allowed_languages: Set of allowed language codes (None = all languages)
        max_pairs_per_language: Maximum pairs per language (None = unlimited)
        max_pairs_total: Maximum total pairs (None = unlimited)
        allowed_paths: Set of allowed file paths (relative to drama_name). If provided,
                      only pairs matching these paths will be included. Paths can be
                      video or subtitle paths, and matching is done by checking if the
                      pair's video_path or subtitle_path is in allowed_paths.
    
    Returns:
        List of FilePairInfo objects, sorted by (language, episode)
    """
    if source_bucket is None:
        source_bucket = settings.pipeline_gcs_source_bucket
    
    storage_client = storage.Client()
    prefix = drama_name.strip("/")
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"
    
    blobs = storage_client.list_blobs(source_bucket, prefix=prefix)
    
    # Collect video and subtitle paths
    videos: Dict[str, str] = {}  # episode -> blob_path
    subtitles: Dict[str, Dict[str, str]] = {}  # language -> episode -> blob_path
    
    for blob in blobs:
        blob_name = blob.name
        # Remove drama_name prefix to get relative path
        rel_path = blob_name
        if prefix and blob_name.startswith(prefix):
            rel_path = blob_name[len(prefix):]
        rel_path = rel_path.lstrip("/")
        
        if not rel_path:
            continue
        
        filename = Path(rel_path).name.lower()
        
        # Check if it's a video file
        if _is_video_file(filename):
            episode = extract_episode(rel_path)
            if episode:
                videos[episode] = rel_path
        elif ".srt" in filename.lower():
            # Check if it's a subtitle file (handle cases like ".srt의 사본의 사본")
            # Find .srt in the filename and check if there's no other extension after it
            srt_idx = filename.lower().find(".srt")
            if srt_idx >= 0:
                after_srt = filename[srt_idx + 4:]
                # If nothing after .srt, or no other dot (indicating another extension) in the next 20 chars
                if not after_srt or "." not in after_srt[:20]:
                    episode = extract_episode(rel_path)
                    if not episode:
                        continue
                    language = detect_language(rel_path)
                    subtitles.setdefault(language, {})[episode] = rel_path
    
    # Build pairs
    pairs: List[FilePairInfo] = []
    for language, episodes in subtitles.items():
        for episode, subtitle_path in episodes.items():
            video_path = videos.get(episode)
            if not video_path:
                continue
            pairs.append(
                FilePairInfo(
                    episode=episode,
                    language=language,
                    video_path=video_path,
                    subtitle_path=subtitle_path,
                )
            )
    
    # Sort by (language, episode) - same as Worker
    sorted_pairs = sorted(pairs, key=lambda item: (item.language, item.episode))
    
    if not sorted_pairs:
        return []
    
    # Apply filters
    filtered: List[FilePairInfo] = []
    per_lang_counts: Dict[str, int] = defaultdict(int)
    allowed = allowed_languages
    
    def normalize_language_key(language: str) -> str:
        """Normalize language key (same as Worker).
        
        Handles variations like:
        - "th_translated" -> "th"
        - "zh-CN" -> "zh"
        - "en_US" -> "en"
        """
        if not language:
            return ""
        lowered = language.strip().lower()
        for delimiter in ("_", "-", " "):
            if delimiter in lowered:
                return lowered.split(delimiter)[0]
        return lowered
    
    for pair in sorted_pairs:
        # Filter by allowed_paths if provided
        # This allows manual jobs to only process selected files
        if allowed_paths is not None:
            # Log detailed path matching information for debugging
            if len(filtered) == 0:  # Only log once at the start
                print(f"[discover_file_pairs] 🔍 开始文件路径过滤:")
                print(f"   allowed_paths: {allowed_paths}")
                print(f"   总配对数量（过滤前）: {len(sorted_pairs)}")
            # Check if either video_path or subtitle_path matches any allowed path
            # Normalize paths for comparison (remove leading/trailing slashes)
            video_match = False
            subtitle_match = False
            
            pair_video = pair.video_path.strip().lstrip("/")
            pair_subtitle = pair.subtitle_path.strip().lstrip("/")
            
            for allowed_path in allowed_paths:
                allowed_normalized = allowed_path.strip().lstrip("/")
                
                # Case 1: Exact match
                if pair_video == allowed_normalized or pair_subtitle == allowed_normalized:
                    video_match = True
                    subtitle_match = True
                    break
                
                # Case 2: allowed_path is a directory, check if file is in that directory
                # Normalize directory path (ensure it ends with / for directory matching)
                if not allowed_normalized.endswith("/"):
                    # Check if it's a directory by checking if any file path starts with it
                    if pair_video.startswith(allowed_normalized + "/") or pair_subtitle.startswith(allowed_normalized + "/"):
                        video_match = True
                        subtitle_match = True
                        break
                else:
                    # Already ends with /, it's definitely a directory
                    if pair_video.startswith(allowed_normalized) or pair_subtitle.startswith(allowed_normalized):
                        video_match = True
                        subtitle_match = True
                        break
                
                # Case 3: allowed_path is a file, check if pair path matches
                # This handles cases where user selects specific files
                if "." in allowed_normalized.split("/")[-1]:  # Likely a file (has extension)
                    if pair_video == allowed_normalized or pair_subtitle == allowed_normalized:
                        video_match = True
                        subtitle_match = True
                        break
            
            # IMPORTANT: Both video AND subtitle must match allowed_paths
            # This ensures that when user selects specific directories, only pairs
            # where BOTH video and subtitle are in selected directories are included
            if not video_match or not subtitle_match:
                # Log first few skipped pairs for debugging
                if len(filtered) < 3:
                    print(f"[discover_file_pairs] ⏭️  跳过配对 (ep{pair.episode}, {pair.language}):")
                    print(f"      video_path: {pair.video_path}")
                    print(f"      subtitle_path: {pair.subtitle_path}")
                    print(f"      原因: 视频匹配={video_match}, 字幕匹配={subtitle_match} (需要两者都匹配)")
                continue
            
            # Log first few matched pairs for debugging
            if len(filtered) < 3:
                print(f"[discover_file_pairs] ✅ 匹配配对 (ep{pair.episode}, {pair.language}):")
                print(f"      video_path: {pair.video_path}")
                print(f"      subtitle_path: {pair.subtitle_path}")
                print(f"      匹配的 allowed_path: {allowed_normalized if 'allowed_normalized' in locals() else 'N/A'}")
        
        # Normalize language key before comparison
        # This ensures "th_translated" matches "th" in allowed_languages
        lang_key = normalize_language_key(pair.language)
        if allowed and lang_key not in allowed:
            continue
        if (
            max_pairs_per_language is not None
            and per_lang_counts[lang_key] >= max_pairs_per_language
        ):
            continue
        if max_pairs_total is not None and len(filtered) >= max_pairs_total:
            break
        filtered.append(pair)
        per_lang_counts[lang_key] += 1
    
    # Log final filtering result
    if allowed_paths is not None:
        print(f"[discover_file_pairs] ✅ 文件路径过滤完成:")
        print(f"   过滤前: {len(sorted_pairs)} 个配对")
        print(f"   过滤后: {len(filtered)} 个配对")
        print(f"   过滤率: {len(filtered)/len(sorted_pairs)*100:.1f}%")
    
    return filtered

