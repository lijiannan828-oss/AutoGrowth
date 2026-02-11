"""Cloud Run job responsible for processing dramas via FFmpeg."""

from __future__ import annotations

import gc
import multiprocessing
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import chardet
from google.cloud import storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP, ArrayUnion, Increment
from google.cloud import firestore

from app.core.config import settings
from app.core.firestore import get_firestore_client, init_firestore
from app.services.pipeline_discovery_service import discover_file_pairs, FilePairInfo
from app.services.concurrency_service import ConcurrencyService

COLLECTION_NAME = "pipeline_jobs"
FAILURE_COLLECTION_NAME = "processing_failures"
EPISODE_REGEX = re.compile(r"(?:ep|episode|e)?[-_\s]*(\d{1,3})", re.IGNORECASE)


def _log(message: str) -> None:
    print(f"[process-worker] {message}", flush=True)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少必要的环境变量：{name}")
    return value


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg"):
        return
    raise RuntimeError("未检测到 ffmpeg，请先安装（如：brew install ffmpeg）")


def download_with_progress(blob: storage.Blob, destination: Path, label: str) -> None:
    total_bytes = blob.size or 0
    chunk_size = 1024 * 1024  # 1MB
    threshold_bytes = max(10 * chunk_size, int(total_bytes * 0.05)) if total_bytes else 10 * chunk_size
    downloaded = 0
    last_report = 0

    with blob.open("rb") as reader, destination.open("wb") as writer:
        while True:
            chunk = reader.read(chunk_size)
            if not chunk:
                break
            writer.write(chunk)
            downloaded += len(chunk)
            if downloaded - last_report >= threshold_bytes:
                if total_bytes:
                    percent = downloaded / total_bytes * 100
                    _log(
                        f"⬇️ Downloading {label}: {percent:.1f}% "
                        f"({downloaded/1024/1024:.1f}MB / {total_bytes/1024/1024:.1f}MB)"
                    )
                else:
                    _log(f"⬇️ Downloading {label}: {downloaded/1024/1024:.1f}MB")
                last_report = downloaded

    if total_bytes and downloaded < total_bytes:
        _log(
            f"⬇️ Downloading {label}: 100% "
            f"({downloaded/1024/1024:.1f}MB / {total_bytes/1024/1024:.1f}MB)"
        )

def extract_episode(source: str) -> str | None:
    """Extract episode number from filename.
    
    Prioritizes numbers after "episode" keyword, then falls back to any episode-like pattern.
    This handles cases like "[k29]runawayprincessecretvacation_episode000.mp4" where
    we want to extract "000" (from episode000) rather than "29" (from [k29]).
    """
    filename = Path(source).stem
    
    # First, try to find "episode" followed by a number (case-insensitive)
    episode_pattern = re.compile(r"episode[-_\s]*(\d{1,3})", re.IGNORECASE)
    match = episode_pattern.search(filename)
    if match:
        return f"{int(match.group(1)):03d}"
    
    # Fall back to general episode pattern
    match = EPISODE_REGEX.search(filename)
    if not match:
        return None
    return f"{int(match.group(1)):03d}"


LANG_FROM_FILENAME = re.compile(r"(?:[_\.-]([a-zA-Z]{2,5}(?:-[A-Za-z0-9]+)?))$")


def _looks_like_language_folder(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_\-]+", name))


def detect_language(relative_path: str) -> str:
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
        candidate_lower = candidate_clean.lower()
        if candidate_lower in ignore_tokens:
            continue
        if "." in candidate_clean:
            break
        if _looks_like_language_folder(candidate_clean):
            language = candidate_clean
            found = True
            break
    if not found:
        filename = parts[-1]
        match = LANG_FROM_FILENAME.search(Path(filename).stem)
        if match:
            language = match.group(1)

    return language.replace(" ", "_")


def normalize_subtitle_encoding(subtitle_path: Path) -> None:
    """Normalize subtitle file encoding to UTF-8.
    
    Tries multiple encoding detection strategies:
    1. Check for UTF-8 BOM
    2. Try UTF-8 directly
    3. Use chardet for detection
    4. Fallback to common encodings
    
    Uses errors="replace" instead of "ignore" to preserve character count
    and avoid silent data loss.
    """
    raw = subtitle_path.read_bytes()
    
    # Strategy 1: Check for UTF-8 BOM
    if raw.startswith(b'\xef\xbb\xbf'):
        text = raw[3:].decode("utf-8", errors="replace")
        subtitle_path.write_text(text, encoding="utf-8")
        return
    
    # Strategy 2: Try UTF-8 directly (most common)
    try:
        text = raw.decode("utf-8", errors="strict")
        # If successful, check if file already has correct encoding
        # Only rewrite if we detected BOM or other issues
        subtitle_path.write_text(text, encoding="utf-8")
        return
    except UnicodeDecodeError:
        pass  # Not UTF-8, continue to detection
    
    # Strategy 3: Use chardet for detection
    detection = chardet.detect(raw)
    detected_encoding = (detection.get("encoding") or "utf-8").lower()
    confidence = detection.get("confidence", 0)
    
    # If chardet detected UTF-8 with high confidence, use it
    if detected_encoding == "utf-8" and confidence > 0.7:
        text = raw.decode("utf-8", errors="replace")
        subtitle_path.write_text(text, encoding="utf-8")
        return
    
    # Strategy 4: Try detected encoding (with fallback to common encodings)
    encodings_to_try = [
        detected_encoding,
        "utf-8",
        "latin-1",  # Common fallback
        "cp1252",   # Windows-1252
        "iso-8859-1",
    ]
    
    for encoding in encodings_to_try:
        if not encoding or encoding == "unknown":
            continue
        try:
            text = raw.decode(encoding, errors="replace")
            subtitle_path.write_text(text, encoding="utf-8")
            return
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Last resort: force UTF-8 with replacement
    text = raw.decode("utf-8", errors="replace")
    subtitle_path.write_text(text, encoding="utf-8")


def get_default_font_name() -> str:
    system = platform.system()
    if system == "Darwin":
        return "PingFang SC"
    if system == "Windows":
        return "Microsoft YaHei"
    return "Noto Sans CJK SC"


LANGUAGE_FONT_PREFERENCES: Dict[str, List[str]] = {
    # CJK (中日韩)
    "ko": ["NanumMyeongjo", "Noto Serif CJK KR", "AppleMyungjo", "Batang"],
    "ja": ["Noto Sans CJK JP", "Hiragino Sans", "Yu Gothic", "Noto Sans"],
    "zh": ["Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", "Noto Sans"],
    
    # Latin-based languages (使用通用 Noto Sans)
    "en": ["Noto Sans", "Helvetica", "Arial"],
    "es": ["Noto Sans", "Helvetica", "Arial"],
    "fr": ["Noto Sans", "Arial", "Helvetica"],
    "de": ["Noto Sans", "Arial", "Helvetica"],
    "pt": ["Noto Sans", "Arial", "Helvetica"],
    "it": ["Noto Sans", "Arial", "Helvetica"],
    
    # Southeast Asian languages
    "th": [
        "NotoSansThai",  # No space variant (PostScript name)
        "Noto Sans Thai",  # With space (full name)
        "Noto Sans Thai UI",  # UI variant
        "NotoSansThai-Regular",  # Regular variant
        "NotoSansThai",  # Base name
        "Noto Sans",  # Fallback
    ],
    "hi": [
        "NotoSansDevanagari",  # No space variant (PostScript name)
        "Noto Sans Devanagari",  # With space (full name)
        "Noto Sans Devanagari UI",  # UI variant
        "NotoSansDevanagari-Regular",  # Regular variant
        "Noto Sans",  # Fallback
    ],
    "id": ["NotoSans", "Noto Sans", "Arial"],
    "vi": ["NotoSans", "Noto Sans", "Arial"],
    
    # Other scripts
    "ar": ["Noto Sans Arabic", "Noto Sans"],
    "ru": ["Noto Sans Cyrillic", "Noto Sans"],
    
    # Default fallback
    "_default": ["Noto Sans", "Noto Sans CJK SC", "Arial"],
}

STYLE_PARAMETERS = {
    "FontSize": "12",
    "PrimaryColour": "&H00FFFFFF",
    "OutlineColour": "&H00000000",
    "BorderStyle": "1",
    "Outline": "1",
    "Shadow": "0",
    "Alignment": "2",
    "MarginV": "50",
    "MarginL": "10",
    "MarginR": "10",
    "WrapStyle": "0",
    "Spacing": "0",
    "Encoding": "1",
}


def normalize_language_key(language: str | None) -> str:
    if not language:
        return ""
    lowered = language.strip().lower()
    for delimiter in ("_", "-", " "):
        if delimiter in lowered:
            return lowered.split(delimiter)[0]
    return lowered


def _font_for_language(language: str, default_font: str) -> str:
    lang_key = normalize_language_key(language)
    preferences = LANGUAGE_FONT_PREFERENCES.get(lang_key, [])
    fallback_preferences = LANGUAGE_FONT_PREFERENCES.get("_default", [])

    for candidate in preferences or []:
        if candidate:
            return candidate

    for candidate in fallback_preferences:
        if candidate:
            return candidate

    return default_font


def detect_fonts_dir() -> str | None:
    system = platform.system()
    candidates: List[Path] = []

    if system == "Windows":
        win_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        candidates.append(win_dir / "Fonts")
    else:
        candidates.extend(
            [
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                Path("/System/Library/Fonts"),
                Path("/Library/Fonts"),
                Path.home() / "Library/Fonts",
                Path.home() / ".fonts",
            ]
        )

    for path in candidates:
        if path.exists():
            path_str = str(path)
            if ":" in path_str:
                continue
            return path_str
    return None


def _check_font_available(font_name: str, fonts_dir: str | None = None) -> bool:
    """Check if a font is available in the system.
    
    Uses fc-list to verify font availability, or checks fonts_dir if provided.
    
    Args:
        font_name: Font name to check
        fonts_dir: Optional fonts directory path
        
    Returns:
        True if font appears to be available, False otherwise
    """
    # If fonts_dir is provided, try to find font files
    if fonts_dir:
        fonts_path = Path(fonts_dir)
        if fonts_path.exists():
            # Search for font files matching the font name (case-insensitive)
            font_name_lower = font_name.lower().replace(" ", "")
            for font_file in fonts_path.rglob("*.ttf"):
                if font_name_lower in font_file.name.lower():
                    return True
            for font_file in fonts_path.rglob("*.otf"):
                if font_name_lower in font_file.name.lower():
                    return True
    
    # Try using fc-list to check font availability
    if shutil.which("fc-list"):
        try:
            # Search for font by family name
            cmd = ["fc-list", f":family={font_name}", "family"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
        except Exception:
            pass
    
    return False


def build_subtitle_style(language: str, default_font: str, fonts_dir: str | None = None) -> Tuple[str, str]:
    """Build subtitle style string with font selection.
    
    IMPLEMENTATION: Smart fallback strategy for complex scripts (th, hi, ar, etc.)
    - For th/hi: Use generic "Sans" font name to let Fontconfig find the best match
    - For other complex scripts: Use font preferences if available, otherwise fallback
    - DO NOT force specific font names for complex scripts to avoid matching failures
    - For Arabic (ar/ar_translated): Use FontSize=20 for better readability
    
    Args:
        language: Language code (e.g., "th", "hi", "ar", "ar_translated")
        default_font: Default font name to use as fallback
        fonts_dir: Optional fonts directory path (not used for font selection, kept for compatibility)
        
    Returns:
        Tuple of (style_string, font_name_used)
    """
    lang_key = normalize_language_key(language)
    
    # Complex scripts that should use Fontconfig fallback mechanism
    # For th/hi: Always use generic "Sans" to let Fontconfig find the best font
    # This avoids font name matching failures
    if lang_key in {"th", "hi"}:
        # Use generic Sans font name - Fontconfig will automatically select
        # the best font for Thai/Hindi from system fonts
        font_name = "Sans"
        _log(f"🔄 使用通用字体 'Sans' 以启用 Fontconfig fallback (语言: {lang_key})")
        _log(f"   Fontconfig 将自动选择系统中最适合 {lang_key.upper()} 的字体")
    else:
        # For other languages, use normal font selection logic
        font_name = _font_for_language(language, default_font)
    
    # Build style parameters, with special handling for Arabic
    style_parts = [f"FontName={font_name}"]
    for key, value in STYLE_PARAMETERS.items():
        # Special case: Arabic language uses FontSize=20 for better readability
        # This only affects font size, not line wrapping (WrapStyle remains unchanged)
        if key == "FontSize" and lang_key == "ar":
            style_parts.append(f"{key}=20")
            _log(f"📏 阿拉伯语字幕使用字号 20 (语言: {language})")
        else:
            style_parts.append(f"{key}={value}")
    style = ",".join(style_parts)
    return style, font_name


def parse_gs_uri(path: str) -> Tuple[str, str]:
    if not path or not path.startswith("gs://"):
        raise ValueError(f"无效的 GCS 路径：{path}")
    remainder = path[5:]
    if "/" not in remainder:
        raise ValueError(f"缺少对象路径：{path}")
    bucket, blob_path = remainder.split("/", 1)
    if not bucket or not blob_path:
        raise ValueError(f"缺少 bucket 或对象：{path}")
    return bucket, blob_path


def format_blob_uri(blob: storage.Blob) -> str:
    return f"gs://{blob.bucket.name}/{blob.name}"


@dataclass
class SubtitlePair:
    episode: str
    language: str
    video_blob: storage.Blob
    subtitle_blob: storage.Blob
    subtitle_path: str


class DramaProcessWorker:
    def __init__(self) -> None:
        init_firestore()
        self.firestore = get_firestore_client()
        self.storage_client = storage.Client()
        self.job_id = _require_env("JOB_ID")
        self.job_ref = self.firestore.collection(COLLECTION_NAME).document(self.job_id)
        snapshot = self.job_ref.get()
        if not snapshot.exists:
            raise RuntimeError(f"Firestore 文档 {self.job_id} 不存在")
        self.job_data = snapshot.to_dict() or {}
        self.drama_name = (
            self.job_data.get("drama_name")
            or self.job_data.get("gdrive_path", "").split("/")[-1]
        ).strip()
        if not self.drama_name:
            raise RuntimeError("job 文档缺少 drama_name")
        self.source_bucket = (
            self.job_data.get("gcs_source_bucket") or settings.pipeline_gcs_source_bucket
        ).strip()
        self.processed_bucket = (
            self.job_data.get("gcs_processed_bucket")
            or settings.pipeline_gcs_processed_bucket
            or f"{self.source_bucket}-processed"
        ).strip()
        self.failures_collection = self.firestore.collection(FAILURE_COLLECTION_NAME)
        self.job_type = (self.job_data.get("type") or "standard").lower()
        self.related_failure_id = self.job_data.get("related_failure_id")
        self.manual_file_paths = (
            self.job_data.get("manual_file_paths")
            or self.job_data.get("file_paths")
            or []
        )
        self.default_font = get_default_font_name()
        self.fonts_dir = detect_fonts_dir()
        
        # Font diagnostic: Check available fonts for Thai and Hindi
        self._diagnose_fonts()
        
        raw_languages = self.job_data.get("process_languages") or []
        self.allowed_languages = {
            str(lang).strip().lower() for lang in raw_languages if str(lang).strip()
        }
        max_pairs = self.job_data.get("max_pairs_per_language")
        self.max_pairs_per_language = int(max_pairs) if max_pairs else None
        total_limit = self.job_data.get("max_pairs_total")
        self.max_pairs_total = int(total_limit) if total_limit else None
        
        # Sharding: Get Cloud Run Task index and count
        self.task_index = int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0"))
        self.task_count = int(os.environ.get("CLOUD_RUN_TASK_COUNT", "1"))
    
    def _diagnose_fonts(self) -> None:
        """Diagnose available fonts for Thai and Hindi languages.
        
        Executes fc-list commands to check what fonts are actually available
        in the system for these languages. This helps debug font matching issues.
        
        CRITICAL: Prints complete output to _log for Cloud Logging visibility.
        """
        _log("🔍 开始字体诊断...")
        
        # Check if fc-list is available
        fc_list_path = shutil.which("fc-list")
        if not fc_list_path:
            _log("⚠️  fc-list 命令不可用，跳过字体诊断")
            _log("   请检查 fontconfig 是否已安装")
            return
        else:
            _log(f"✅ fc-list 可用: {fc_list_path}")
        
        # Check font directories
        _log("📁 检查字体目录:")
        font_dirs = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            "/usr/share/fonts/truetype/noto",
        ]
        for font_dir in font_dirs:
            if Path(font_dir).exists():
                noto_files = list(Path(font_dir).rglob("*noto*thai*.ttf")) + list(Path(font_dir).rglob("*noto*thai*.otf"))
                devanagari_files = list(Path(font_dir).rglob("*noto*devanagari*.ttf")) + list(Path(font_dir).rglob("*noto*devanagari*.otf"))
                _log(f"   {font_dir}:")
                _log(f"     泰语字体文件: {len(noto_files)} 个")
                if noto_files:
                    _log(f"       示例: {noto_files[0].name}")
                _log(f"     印地语字体文件: {len(devanagari_files)} 个")
                if devanagari_files:
                    _log(f"       示例: {devanagari_files[0].name}")
        
        # Languages to diagnose
        languages_to_check = ["th", "hi"]
        
        for lang_code in languages_to_check:
            try:
                # Execute fc-list :lang=<lang_code>
                cmd = ["fc-list", f":lang={lang_code}"]
                _log(f"📋 执行命令: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                _log(f"   返回码: {result.returncode}")
                if result.stderr:
                    _log(f"   stderr: {result.stderr}")
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if output:
                        # Print COMPLETE output to _log (as requested)
                        _log(f"📋 系统可用的 {lang_code.upper()} 字体完整输出:")
                        _log("=" * 60)
                        _log(output)
                        _log("=" * 60)
                        
                        lines = output.split("\n")
                        _log(f"📊 统计: 共 {len(lines)} 个字体条目")
                        
                        # Extract font family names (simplified parsing)
                        font_families = set()
                        for line in lines:
                            # fc-list format: /path/to/font: Font Family Name:style=Style
                            parts = line.split(":")
                            if len(parts) >= 2:
                                family_part = parts[1].strip()
                                # Remove style information
                                if ":" in family_part:
                                    family_part = family_part.split(":")[0]
                                font_families.add(family_part)
                        
                        if font_families:
                            _log(f"📝 {lang_code.upper()} 字体 Family Names (去重后，共 {len(font_families)} 个):")
                            for family in sorted(font_families):
                                _log(f"   - {family}")
                    else:
                        _log(f"⚠️  未找到 {lang_code.upper()} 语言的字体")
                        _log(f"   尝试检查所有 Noto 字体...")
                        # Try listing all Noto fonts
                        cmd_all = ["fc-list", ":family=Noto", "family"]
                        result_all = subprocess.run(cmd_all, capture_output=True, text=True, timeout=5)
                        if result_all.returncode == 0 and result_all.stdout.strip():
                            _log(f"   找到的 Noto 字体:")
                            for line in result_all.stdout.strip().split("\n")[:10]:
                                _log(f"     {line}")
                else:
                    _log(f"⚠️  fc-list :lang={lang_code} 执行失败 (returncode={result.returncode}):")
                    _log(f"   stderr: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                _log(f"⚠️  fc-list :lang={lang_code} 执行超时")
            except Exception as e:
                _log(f"⚠️  字体诊断出错 ({lang_code}): {e}")
                import traceback
                _log(f"   详细错误: {traceback.format_exc()}")
        
        _log("✅ 字体诊断完成")

    def run(self) -> None:
        env = settings.app_env
        if env == "development":
            _log("🔧 [DEV] Running in local mode")
            if not settings.google_application_credentials:
                raise RuntimeError("开发环境需设置 GOOGLE_APPLICATION_CREDENTIALS")
        else:
            _log("🏭 [PROD] Running in Cloud Run")

        ensure_ffmpeg()
        manual_paths = (
            self.manual_file_paths
            if isinstance(self.manual_file_paths, list)
            else []
        )
        
        # CRITICAL FIX: Use PipelineDiscoveryService for consistent sorting
        # This ensures Service and Worker use the exact same file discovery logic
        if self.job_type == "retry":
            # Retry jobs use specific paths, keep existing logic
            all_pairs = self._build_retry_pairs()
        elif manual_paths:
            # Manual jobs: Use shared discovery service for consistency
            # This ensures Service and Worker use the same file discovery logic
            # Previously used _build_manual_pairs which had path matching issues
            # Pass manual_paths as allowed_paths to filter by selected files
            _log(f"📁 手动任务文件路径过滤:")
            _log(f"   manual_paths: {manual_paths}")
            _log(f"   allowed_languages: {self.allowed_languages}")
            _log(f"   开始调用 discover_file_pairs...")
            
            try:
                file_pairs = discover_file_pairs(
                    drama_name=self.drama_name,
                    source_bucket=self.source_bucket,
                    allowed_languages=self.allowed_languages if self.allowed_languages else None,
                    max_pairs_per_language=self.max_pairs_per_language,
                    max_pairs_total=self.max_pairs_total,
                    allowed_paths=set(manual_paths) if manual_paths else None,
                )
                _log(f"✅ discover_file_pairs 调用成功，返回 {len(file_pairs)} 个配对")
            except TypeError as e:
                _log(f"❌ discover_file_pairs 调用失败: {e}")
                _log(f"   错误类型: TypeError - 可能是代码版本不匹配")
                _log(f"   请检查 Worker 镜像是否已更新到最新版本")
                raise
            # Convert FilePairInfo to SubtitlePair with Blob objects
            all_pairs = self._convert_file_pairs_to_subtitle_pairs(file_pairs)
        else:
            # Standard jobs: Use shared discovery service for consistent sorting
            file_pairs = discover_file_pairs(
                drama_name=self.drama_name,
                source_bucket=self.source_bucket,
                allowed_languages=self.allowed_languages if self.allowed_languages else None,
                max_pairs_per_language=self.max_pairs_per_language,
                max_pairs_total=self.max_pairs_total,
            )
            # Convert FilePairInfo to SubtitlePair with Blob objects
            all_pairs = self._convert_file_pairs_to_subtitle_pairs(file_pairs)
        
        # Sharding: Apply modulo algorithm to filter pairs for this task
        pairs = [
            pair for i, pair in enumerate(all_pairs) 
            if i % self.task_count == self.task_index
        ]
        
        _log(
            f"📊 Task {self.task_index}/{self.task_count}: "
            f"Claimed {len(pairs)} of {len(all_pairs)} episodes"
        )
        
        # Resume check: Skip already processed files if Task document exists
        task_ref = self.job_ref.collection("tasks").document(str(self.task_index))
        task_snapshot = task_ref.get()
        
        if task_snapshot.exists:
            task_data = task_snapshot.to_dict() or {}
            success_files = task_data.get("success_files", [])
            
            if success_files:
                # Create a set of already processed file identifiers for fast lookup
                processed_identifiers = set(success_files)
                
                # Filter out already processed pairs
                original_count = len(pairs)
                pairs = [
                    pair for pair in pairs
                    if self._get_file_identifier(pair) not in processed_identifiers
                ]
                skipped_count = original_count - len(pairs)
                
                _log(
                    f"🔄 Task {self.task_index}/{self.task_count}: "
                    f"Skipping {skipped_count} already processed files "
                    f"(remaining: {len(pairs)}/{original_count})"
                )
            else:
                _log(
                    f"📝 Task {self.task_index}/{self.task_count}: "
                    f"Task document exists but no success_files, processing all {len(pairs)} episodes"
                )
        else:
            _log(
                f"📝 Task {self.task_index}/{self.task_count}: "
                f"Task document does not exist, processing all {len(pairs)} episodes"
            )
        
        total = len(pairs)
        if total == 0:
            if len(all_pairs) == 0:
                self._mark_failure("未在 GCS 中找到可压制的 mp4/srt 配对")
            else:
                _log(
                    f"⚠️ Task {self.task_index}/{self.task_count}: "
                    f"No episodes assigned to this task (total: {len(all_pairs)})"
                )
            return

        # Initialize or update Task status document in Firestore
        if task_snapshot.exists:
            # Update existing task document
            task_ref.update(
                {
                    "status": "RUNNING",
                    "current_file": None,
                    "total_count": total,  # Update total_count in case pairs changed
                    "updated_at": SERVER_TIMESTAMP,
                }
            )
            _log(
                f"📝 Task {self.task_index}/{self.task_count}: "
                f"Updated existing Firestore task document (remaining: {total} episodes)"
            )
        else:
            # Create new task document
            task_ref.set(
                {
                    "task_index": self.task_index,
                    "status": "RUNNING",
                    "current_file": None,
                    "success_files": [],
                    "failed_files": [],
                    "progress_count": 0,
                    "total_count": total,
                    "created_at": SERVER_TIMESTAMP,
                    "updated_at": SERVER_TIMESTAMP,
                }
            )
            _log(
                f"📝 Task {self.task_index}/{self.task_count}: "
                f"Initialized Firestore task document (total: {total} episodes)"
            )

        # Update main job: set total_files if not already set, and update status
        # This ensures total_files is set even if service didn't set it
        update_data = {
            "status": "PROCESSING",
            "stage": 2,
            "updated_at": SERVER_TIMESTAMP,
        }
        
        # Set total_files if not already set (for manual jobs that don't know count upfront)
        job_snapshot = self.job_ref.get()
        job_data = job_snapshot.to_dict() or {}
        if job_data.get("total_files") is None:
            update_data["total_files"] = len(all_pairs)  # Total across all tasks
            _log(f"📊 Set total_files={len(all_pairs)} in main job document")
        
        # Ensure processed_files and failed_files are initialized
        if "processed_files" not in job_data:
            update_data["processed_files"] = 0
        if "failed_files" not in job_data:
            update_data["failed_files"] = 0
        
        # Update progress to reflect actual processing status
        # Clear any queued status message and show actual progress
        total_files = update_data.get("total_files") or job_data.get("total_files") or len(all_pairs)
        update_data["progress"] = f"开始处理（共 {total_files} 个文件，{self.task_count} 个任务并行）"
        
        self.job_ref.update(update_data)

        processed_bucket = self.storage_client.bucket(self.processed_bucket)
        successes = 0
        with tempfile.TemporaryDirectory(prefix="process-worker-") as tmpdir:
            temp_dir = Path(tmpdir)
            attempt = 0
            for pair in pairs:
                attempt += 1
                if self._process_single_pair(
                    pair, processed_bucket, temp_dir, attempt, total, task_ref
                ):
                    successes += 1

        # Update Task status to COMPLETED
        task_ref.update(
            {
                "status": "COMPLETED",
                "current_file": None,
                "updated_at": SERVER_TIMESTAMP,
            }
        )
        _log(
            f"✅ Task {self.task_index}/{self.task_count}: "
            f"Completed processing ({successes} succeeded, {total - successes} failed)"
        )

        # Use Transaction to check if all files are processed and update main job status
        @firestore.transactional
        def check_and_update_job_status(transaction):
            """Transaction to atomically check and update job status."""
            job_snapshot = self.job_ref.get(transaction=transaction)
            if not job_snapshot.exists:
                _log("⚠️ Job document does not exist, skipping status update")
                return
            
            job_data = job_snapshot.to_dict() or {}
            processed_files = job_data.get("processed_files", 0)
            failed_files = job_data.get("failed_files", 0)
            total_files = job_data.get("total_files", 0)
            
            # Check if all files are processed
            if processed_files + failed_files >= total_files:
                # Determine final status
                if failed_files == total_files:
                    # All files failed
                    final_status = "FAILED"
                    final_message = f"所有文件压制失败（共 {total_files} 个）"
                elif failed_files == 0:
                    # All files succeeded
                    final_status = "SUCCEEDED"
                    final_message = f"全部压制完成（共 {total_files} 个）"
                else:
                    # Partial success
                    final_status = "SUCCEEDED"
                    final_message = f"压制完成（成功 {processed_files} 个，失败 {failed_files} 个）"
                
                # Atomically update main job status
                transaction.update(
                    self.job_ref,
                    {
                        "status": final_status,
                        "stage": 2,
                        "progress": final_message,
                        "last_event": {
                            "type": "PROCESS_COMPLETED",
                            "timestamp": SERVER_TIMESTAMP,
                        },
                        "updated_at": SERVER_TIMESTAMP,
                    },
                )
                _log(
                    f"🎯 Main job status updated to {final_status}: "
                    f"{processed_files} processed, {failed_files} failed, {total_files} total"
                )
            else:
                _log(
                    f"⏳ Main job not yet complete: "
                    f"{processed_files + failed_files}/{total_files} files processed"
                )

        # Execute transaction
        transaction = self.firestore.transaction()
        try:
            check_and_update_job_status(transaction)
        except Exception as exc:
            _log(f"⚠️ Transaction failed: {exc}")
            # Don't raise - task completion is still valid even if status update fails
        if self.job_type == "retry" and self.related_failure_id and successes > 0:
            self._resolve_failure(self.related_failure_id)
        
        # Release concurrency control slot and trigger next job in queue (FIFO)
        # Check if this is the last task by verifying if job is now complete
        try:
            job_snapshot = self.job_ref.get()
            if job_snapshot.exists:
                job_data = job_snapshot.to_dict() or {}
                status = (job_data.get("status") or "").upper()
                # Only release if job is completed (SUCCEEDED or FAILED)
                # This ensures we only release once when the job actually finishes
                if status in ("SUCCEEDED", "FAILED"):
                    concurrency_service = ConcurrencyService()
                    # Release slot and trigger next job in queue (FIFO)
                    triggered = concurrency_service.release_and_trigger_next(self.job_id)
                    if triggered:
                        _log(f"🚀 Released slot for job_id={self.job_id} and triggered next job in queue")
                    else:
                        _log(f"🔓 Released slot for job_id={self.job_id} (no jobs in queue)")
        except Exception as exc:
            _log(f"⚠️ Error releasing concurrency control slot: {exc}")
            # Don't raise - slot will be cleaned up by timeout mechanism
            # But try to release slot anyway
            try:
                concurrency_service = ConcurrencyService()
                concurrency_service.release_job_slot(self.job_id)
            except Exception as release_exc:
                _log(f"⚠️ Failed to release slot on error: {release_exc}")
        
        _log("🎬 所有集数压制完成")

    def _relative_blob_path(self, blob_name: str) -> str:
        prefix = self.drama_name.strip("/")
        if prefix and blob_name.startswith(f"{prefix}/"):
            return blob_name[len(prefix) + 1 :]
        return blob_name

    def _convert_file_pairs_to_subtitle_pairs(
        self, file_pairs: List[FilePairInfo]
    ) -> List[SubtitlePair]:
        """Convert FilePairInfo (from discovery service) to SubtitlePair (with Blob objects).
        
        CRITICAL: This ensures consistent sorting between Service and Worker.
        Service uses discover_file_pairs() to calculate task_count, and Worker
        must use the same logic to ensure correct sharding.
        
        Args:
            file_pairs: List of FilePairInfo from discovery service (already sorted)
        
        Returns:
            List of SubtitlePair with Blob objects (same order as file_pairs)
        """
        pairs: List[SubtitlePair] = []
        
        for file_pair in file_pairs:
            # Construct full GCS paths (relative to drama_name)
            video_gcs_path = f"{self.drama_name}/{file_pair.video_path}".strip("/")
            subtitle_gcs_path = f"{self.drama_name}/{file_pair.subtitle_path}".strip("/")
            
            # Get Blob objects
            video_bucket = self.storage_client.bucket(self.source_bucket)
            video_blob = video_bucket.blob(video_gcs_path)
            subtitle_blob = video_bucket.blob(subtitle_gcs_path)
            
            # Verify blobs exist
            if not video_blob.exists():
                _log(f"⚠️ Video blob does not exist: {video_gcs_path}")
                continue
            if not subtitle_blob.exists():
                _log(f"⚠️ Subtitle blob does not exist: {subtitle_gcs_path}")
                continue
            
            pairs.append(
                SubtitlePair(
                    episode=file_pair.episode,
                    language=file_pair.language,
                    video_blob=video_blob,
                    subtitle_blob=subtitle_blob,
                    subtitle_path=file_pair.subtitle_path,
                )
            )
        
        _log(f"✅ Converted {len(pairs)} file pairs to SubtitlePair objects (from discovery service)")
        return pairs

    def _register_media_blob(
        self,
        rel_path: str,
        blob: storage.Blob,
        videos: Dict[str, storage.Blob],
        subtitles: Dict[str, Dict[str, Tuple[storage.Blob, str]]],
    ) -> None:
        """Register a media blob as video or subtitle.
        
        Uses the same video file detection logic as PipelineDiscoveryService
        to ensure consistency.
        """
        lower = rel_path.lower()
        filename = Path(rel_path).name.lower()
        
        # Use the same video detection logic as PipelineDiscoveryService
        # Import here to avoid circular dependency
        from app.services.pipeline_discovery_service import _is_video_file
        
        is_video = _is_video_file(filename)
        
        if is_video:
            episode = extract_episode(rel_path)
            if episode:
                videos[episode] = blob
        elif ".srt" in filename.lower():
            # Check if it's a subtitle file (handle cases like ".srt의 사본의 사본")
            # Use the same logic as PipelineDiscoveryService
            srt_idx = filename.lower().find(".srt")
            if srt_idx >= 0:
                after_srt = filename[srt_idx + 4:]
                # If nothing after .srt, or no other dot (indicating another extension) in the next 20 chars
                if not after_srt or "." not in after_srt[:20]:
                    episode = extract_episode(rel_path)
                    if not episode:
                        return
                    language = detect_language(rel_path)
                    subtitles.setdefault(language, {})[episode] = (blob, rel_path)

    def _finalize_pairs(
        self,
        videos: Dict[str, storage.Blob],
        subtitles: Dict[str, Dict[str, Tuple[storage.Blob, str]]],
    ) -> List[SubtitlePair]:
        pairs: List[SubtitlePair] = []
        for language, episodes in subtitles.items():
            for episode, pair in episodes.items():
                subtitle_blob, rel_path = pair
                video_blob = videos.get(episode)
                if not video_blob:
                    continue
                _log(
                    f"🔍 [DEBUG] Found Pair: EP{episode} | Lang: {language} | Sub: {rel_path}"
                )
                pairs.append(
                    SubtitlePair(
                        episode=episode,
                        language=language,
                        video_blob=video_blob,
                        subtitle_blob=subtitle_blob,
                        subtitle_path=rel_path,
                    )
                )

        sorted_pairs = sorted(pairs, key=lambda item: (item.language, item.episode))
        if not sorted_pairs:
            return []

        filtered: List[SubtitlePair] = []
        per_lang_counts: Dict[str, int] = defaultdict(int)
        allowed = self.allowed_languages

        for pair in sorted_pairs:
            lang_key = pair.language.lower()
            if allowed and lang_key not in allowed:
                continue
            if (
                self.max_pairs_per_language is not None
                and per_lang_counts[lang_key] >= self.max_pairs_per_language
            ):
                continue
            if self.max_pairs_total is not None and len(filtered) >= self.max_pairs_total:
                break
            filtered.append(pair)
            per_lang_counts[lang_key] += 1

        return filtered

    def _build_processing_pairs(self) -> List[SubtitlePair]:
        prefix = self.drama_name.strip("/")
        if prefix and not prefix.endswith("/"):
            prefix = f"{prefix}/"
        blobs = self.storage_client.list_blobs(self.source_bucket, prefix=prefix)

        videos: Dict[str, storage.Blob] = {}
        subtitles: Dict[str, Dict[str, Tuple[storage.Blob, str]]] = {}

        for blob in blobs:
            rel_path = self._relative_blob_path(blob.name).lstrip("/")
            if not rel_path:
                continue
            self._register_media_blob(rel_path, blob, videos, subtitles)

        return self._finalize_pairs(videos, subtitles)

    def _build_manual_pairs(self, manual_paths: List[str]) -> List[SubtitlePair]:
        prefix_root = self.drama_name.strip("/")
        base_prefix = f"{prefix_root}/" if prefix_root else ""

        videos: Dict[str, storage.Blob] = {}
        subtitles: Dict[str, Dict[str, Tuple[storage.Blob, str]]] = {}

        for raw_path in manual_paths:
            normalized = (raw_path or "").strip().lstrip("/")
            if not normalized:
                continue
            full_prefix = f"{base_prefix}{normalized}".strip("/")
            lower = normalized.lower()
            if not lower.endswith(".mp4") and not lower.endswith(".srt"):
                full_prefix = f"{full_prefix}/"
            iterator = self.storage_client.list_blobs(
                self.source_bucket,
                prefix=full_prefix,
            )
            for blob in iterator:
                rel_path = self._relative_blob_path(blob.name).lstrip("/")
                if not rel_path:
                    continue
                self._register_media_blob(rel_path, blob, videos, subtitles)

        return self._finalize_pairs(videos, subtitles)
    
    def _build_retry_pairs(self) -> List[SubtitlePair]:
        video_path = self.job_data.get("target_video_path")
        subtitle_path = self.job_data.get("target_subtitle_path")
        if not video_path or not subtitle_path:
            raise RuntimeError("Retry 任务缺少 target_video_path 或 target_subtitle_path")

        video_bucket_name, video_blob_name = parse_gs_uri(video_path)
        subtitle_bucket_name, subtitle_blob_name = parse_gs_uri(subtitle_path)

        video_bucket = self.storage_client.bucket(video_bucket_name)
        subtitle_bucket = self.storage_client.bucket(subtitle_bucket_name)
        video_blob = video_bucket.blob(video_blob_name)
        subtitle_blob = subtitle_bucket.blob(subtitle_blob_name)

        if not video_blob.exists():
            raise RuntimeError(f"Retry 视频不存在：{video_path}")
        if not subtitle_blob.exists():
            raise RuntimeError(f"Retry 字幕不存在：{subtitle_path}")

        episode = extract_episode(video_blob_name) or extract_episode(subtitle_blob_name)
        if not episode:
            raise RuntimeError("无法从路径中解析集数")

        language = detect_language(subtitle_blob_name) or "unknown"
        pair = SubtitlePair(
            episode=episode,
            language=language,
            video_blob=video_blob,
            subtitle_blob=subtitle_blob,
            subtitle_path=subtitle_blob_name,
        )
        _log(
            f"🔁 [Retry] EP{episode} | Lang: {language} | "
            f"Video: {video_blob_name} | Subtitle: {subtitle_blob_name}"
        )
        return [pair]

    def _get_file_identifier(self, pair: SubtitlePair) -> str:
        """Generate file identifier for tracking (consistent with _process_single_pair).
        
        Args:
            pair: SubtitlePair object
        
        Returns:
            File identifier string in format "{language}/ep{episode}.mp4"
        """
        return f"{pair.language}/ep{pair.episode}.mp4"

    def _process_single_pair(
        self,
        pair: SubtitlePair,
        processed_bucket: storage.Bucket,
        temp_dir: Path,
        completed: int,
        total: int,
        task_ref,
    ) -> bool:
        safe_lang = pair.language.replace("/", "_")
        base_name = f"{safe_lang}_ep{pair.episode}"
        video_path = temp_dir / f"{base_name}_input.mp4"
        subtitle_path = temp_dir / f"{base_name}_input.srt"
        output_path = temp_dir / f"{base_name}_output.mp4"
        
        # Generate file identifier for tracking
        file_identifier = self._get_file_identifier(pair)

        # Update current_file before processing
        task_ref.update({"current_file": file_identifier})

        try:
            download_with_progress(
                pair.video_blob,
                video_path,
                f"{pair.language} ep{pair.episode} video",
            )
            download_with_progress(
                pair.subtitle_blob,
                subtitle_path,
                f"{pair.language} ep{pair.episode} subtitle",
            )
            normalize_subtitle_encoding(subtitle_path)

            subtitle_size = subtitle_path.stat().st_size
            _log(f"🔍 [DEBUG] 字幕文件大小 {subtitle_path.name}: {subtitle_size} bytes")
            if subtitle_size == 0:
                _log(f"⚠️ [WARN] 字幕文件 {subtitle_path.name} 为空，请检查源数据")

            preview_lines: List[str] = []
            with subtitle_path.open("r", encoding="utf-8", errors="ignore") as fh:
                for _ in range(10):
                    line = fh.readline()
                    if not line:
                        break
                    preview_lines.append(line.rstrip("\n"))
            preview_text = "\n".join(preview_lines)
            preview_block = (
                f"🔍 [DEBUG] 字幕文件内容预览 ({subtitle_path.name}):\n"
                "--------------------------------------------------\n"
                f"{preview_text}\n"
                "--------------------------------------------------"
            )
            _log(preview_block)

            style, font_used = build_subtitle_style(pair.language, self.default_font, self.fonts_dir)
            vf_components = [f"subtitles={subtitle_path.name}"]
            # REMOVED: fontsdir parameter
            # Reason: We've installed fonts via apt-get and refreshed fc-cache in Dockerfile.
            # Specifying fontsdir may limit libass's search scope and prevent it from finding
            # Noto fonts in system directories. Let it use system Fontconfig configuration.
            vf_components.append(f"force_style='{style}'")
            vf_arg = ":".join(vf_components)
            _log(
                f"🔤 使用字体 {font_used} (使用系统 Fontconfig，不指定 fontsdir)"
            )

            # Get CPU count for FFmpeg thread optimization
            cpu_count = multiprocessing.cpu_count()
            # FFmpeg thread count: Use available CPU cores, but limit to 4 for low-spec containers (2 vCPU)
            # Or use 0 to let FFmpeg auto-detect (recommended for better compatibility)
            threads = min(cpu_count, 4)
            # Alternative: threads = 0  # Let FFmpeg auto-detect (uncomment to use)
            
            cmd = [
                "ffmpeg",
                "-y",
                "-threads",
                str(threads),
                "-i",
                video_path.name,
                "-vf",
                vf_arg,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",  # Optimized for speed (balanced quality/speed)
                "-crf",
                "23",  # Balanced quality and file size (18=high quality, 23=balanced, 28=smaller file)
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",  # Optimize MP4 for web streaming
                output_path.name,
            ]
            _log(
                f"🎞️ 正在压制 {self.drama_name} - {pair.language} - ep{pair.episode} "
                f"(进度 {completed}/{total})"
            )
            _log("🔍 [DEBUG] FFmpeg 执行命令:\n" + " ".join(cmd))
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
                raise RuntimeError(f"FFmpeg 处理失败 (exit={return_code})，请检查日志")

            dest_path = f"{self.drama_name}/{safe_lang}/ep{pair.episode}.mp4"
            output_blob = processed_bucket.blob(dest_path)
            output_blob.upload_from_filename(output_path)
            self._verify_uploaded_blob(output_blob)

            # Update Task document: add to success_files and increment progress_count
            task_ref.update(
                {
                    "success_files": ArrayUnion([file_identifier]),
                    "progress_count": Increment(1),
                    "updated_at": SERVER_TIMESTAMP,
                }
            )
            
            # Atomically update main job document: increment processed_files
            self.job_ref.update(
                {
                    "processed_files": Increment(1),
                    "updated_at": SERVER_TIMESTAMP,
                }
            )
            
            _log(
                f"✅ {pair.language} ep{pair.episode} 完成 "
                f"(Task {self.task_index}/{self.task_count}: {completed}/{total})"
            )
            
            # Explicit resource cleanup: delete temporary files immediately
            self._cleanup_temp_files(video_path, subtitle_path, output_path)
            
            return True
        except Exception:
            error_trace = traceback.format_exc()
            
            # Record failure in processing_failures collection (keep existing logic)
            self._record_failure(pair, error_trace)
            
            # Update Task document: add to failed_files and increment progress_count
            task_ref.update(
                {
                    "failed_files": ArrayUnion(
                        [
                            {
                                "path": file_identifier,
                                "error": error_trace[:500],  # Limit error message length
                            }
                        ]
                    ),
                    "progress_count": Increment(1),
                    "updated_at": SERVER_TIMESTAMP,
                }
            )
            
            # Atomically update main job document: increment failed_files
            self.job_ref.update(
                {
                    "failed_files": Increment(1),
                    "updated_at": SERVER_TIMESTAMP,
                }
            )
            
            _log(
                f"❌ {pair.language} ep{pair.episode} 压制失败 "
                f"(Task {self.task_index}/{self.task_count}: {completed}/{total})，已记录 processing_failures"
            )
            
            # Explicit resource cleanup: delete temporary files even on failure
            self._cleanup_temp_files(video_path, subtitle_path, output_path)
            
            return False

    def _update_progress(self, status: str, progress: str, processed: int, total: int) -> None:
        self.job_ref.update(
            {
                "status": status,
                "stage": 2,
                "progress": progress,
                "processed_files": processed,
                "processed_total": total,
                "updated_at": SERVER_TIMESTAMP,
            }
        )

    def _mark_failure(self, message: str) -> None:
        self.job_ref.update(
            {
                "status": "FAILED",
                "stage": 2,
                "progress": message,
                "last_event": {
                    "type": "PROCESS_FAILED",
                    "error": message,
                    "timestamp": SERVER_TIMESTAMP,
                },
                "updated_at": SERVER_TIMESTAMP,
            }
        )
        raise RuntimeError(message)

    def _verify_uploaded_blob(self, blob: storage.Blob) -> None:
        try:
            blob.reload()
        except Exception as exc:  # pragma: no cover - network failure scenarios
            raise RuntimeError(f"输出文件校验失败：{exc}") from exc

        if not blob.size or blob.size <= 0:
            raise RuntimeError("输出文件大小为 0，压制结果无效")

    def _cleanup_temp_files(
        self, video_path: Path, subtitle_path: Path, output_path: Path
    ) -> None:
        """Explicitly delete temporary files and force garbage collection.
        
        This is crucial for preventing memory accumulation when processing
        hundreds of files in a single task.
        """
        deleted_count = 0
        
        # Delete video input file
        if video_path.exists():
            try:
                video_path.unlink()
                deleted_count += 1
            except Exception as exc:
                _log(f"⚠️ Failed to delete video file {video_path}: {exc}")
        
        # Delete subtitle input file
        if subtitle_path.exists():
            try:
                subtitle_path.unlink()
                deleted_count += 1
            except Exception as exc:
                _log(f"⚠️ Failed to delete subtitle file {subtitle_path}: {exc}")
        
        # Delete output file (if exists, may not exist on failure)
        if output_path.exists():
            try:
                output_path.unlink()
                deleted_count += 1
            except Exception as exc:
                _log(f"⚠️ Failed to delete output file {output_path}: {exc}")
        
        if deleted_count > 0:
            _log(f"🧹 Cleaned up {deleted_count} temporary file(s)")
        
        # Force garbage collection to free memory immediately
        collected = gc.collect()
        if collected > 0:
            _log(f"🗑️  Garbage collected {collected} objects")

    def _record_failure(self, pair: SubtitlePair, error_message: str) -> None:
        document = {
            "job_id": self.job_id,
            "drama_name": self.drama_name,
            "language": pair.language,
            "episode": pair.episode,
            "video_gcs_path": format_blob_uri(pair.video_blob),
            "subtitle_gcs_path": format_blob_uri(pair.subtitle_blob),
            "error_message": error_message,
            "status": "FAILED",
            "job_type": self.job_type,
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
        }
        if self.related_failure_id:
            document["source_failure_id"] = self.related_failure_id

        try:
            doc_ref = self.failures_collection.document()
            doc_ref.set(document)
            _log(f"🧾 已记录失败文档：{doc_ref.id}")
        except Exception as exc:  # pragma: no cover - logging fallback
            _log(f"⚠️ [WARN] 记录 processing_failures 失败：{exc}")

    def _resolve_failure(self, failure_id: str) -> None:
        try:
            self.failures_collection.document(failure_id).update(
                {
                    "status": "RESOLVED",
                    "resolved_at": SERVER_TIMESTAMP,
                    "updated_at": SERVER_TIMESTAMP,
                }
            )
            _log(f"✅ 已更新失败记录 {failure_id} 为 RESOLVED")
        except Exception as exc:  # pragma: no cover
            _log(f"⚠️ [WARN] 更新失败记录 {failure_id} 状态失败：{exc}")


def main() -> None:
    worker = None
    job_id = None
    job_ref = None
    try:
        # Get job_id early so we can update status even if __init__ fails
        job_id = _require_env("JOB_ID")
        init_firestore()
        firestore = get_firestore_client()
        job_ref = firestore.collection(COLLECTION_NAME).document(job_id)
        
        worker = DramaProcessWorker()
        worker.run()
    except Exception as exc:
        _log(f"❌ Worker 执行失败：{exc}")
        error_trace = traceback.format_exc()
        
        # CRITICAL: Update job status to FAILED if it's still QUEUED or PROCESSING
        # This ensures the job status is correct even if worker fails early
        if job_id and job_ref:
            try:
                job_snapshot = job_ref.get()
                if job_snapshot.exists:
                    job_data = job_snapshot.to_dict() or {}
                    current_status = (job_data.get("status") or "").upper()
                    
                    # Only update if status is QUEUED or PROCESSING (not already FAILED/SUCCEEDED)
                    if current_status in ("QUEUED", "PROCESSING", ""):
                        _log(f"📝 更新 job 状态为 FAILED (当前状态: {current_status})")
                        job_ref.update({
                            "status": "FAILED",
                            "progress": f"Worker 执行失败: {str(exc)[:200]}",
                            "updated_at": SERVER_TIMESTAMP,
                        })
                        _log(f"✅ Job 状态已更新为 FAILED")
            except Exception as status_exc:
                _log(f"⚠️ 更新 job 状态失败: {status_exc}")
        
        # Release concurrency control slot on error and trigger next job
        if job_id:
            try:
                concurrency_service = ConcurrencyService()
                # Try to trigger next job even on error (slot is released)
                triggered = concurrency_service.release_and_trigger_next(job_id)
                if triggered:
                    _log(f"🚀 Released slot for failed job_id={job_id} and triggered next job")
                else:
                    _log(f"🔓 Released slot for failed job_id={job_id} (no jobs in queue)")
            except Exception as release_exc:
                _log(f"⚠️ Error releasing concurrency control slot on error: {release_exc}")
                # Fallback: just release slot without triggering next
                try:
                    concurrency_service = ConcurrencyService()
                    concurrency_service.release_job_slot(job_id)
                    _log(f"🔓 Fallback: Released slot for failed job_id={job_id}")
                except Exception as fallback_exc:
                    _log(f"⚠️ Fallback release also failed: {fallback_exc}")
        raise


if __name__ == "__main__":
    main()


