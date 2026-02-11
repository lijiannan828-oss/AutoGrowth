"""Cloud Run worker that syncs selected Google Drive folders to GCS via rclone."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests
from google.cloud import storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.config import settings
from app.core.firestore import get_firestore_client, init_firestore
from app.services.google_oauth_service import retrieve_refresh_token

PROGRESS_REGEX = re.compile(r"Transferred:\s+.*?(\d+)%")
FILTER_COOLDOWN_SECONDS = 2.0


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[transfer-worker {timestamp}] {message}", flush=True)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少必要的环境变量：{name}")
    return value


def _exchange_refresh_token(refresh_token: str) -> Dict[str, str]:
    """Exchange refresh token for a short-lived access token."""
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise RuntimeError("未配置 GOOGLE_OAUTH_CLIENT_ID / SECRET，无法刷新访问令牌")

    payload = {
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"刷新访问令牌失败：{response.text}")
    data = response.json()
    expires_in = data.get("expires_in", 3500)
    expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in) - 60)
    token_payload = {
        "access_token": data.get("access_token"),
        "token_type": data.get("token_type", "Bearer"),
        "refresh_token": refresh_token,
        "expiry": expiry.isoformat().replace("+00:00", "Z"),
    }
    return token_payload


def _fix_gdrive_path(gdrive_path: str) -> str:
    """修正 Google Drive 路径中的下划线为空格。

    配置的 label 使用下划线（如 CN_Programs），
    但 Google Drive 真实文件夹名使用空格（如 CN Programs）。

    只替换根目录部分的下划线，不影响剧集名称。
    例如: CN_Programs/KR085... -> CN Programs/KR085...
    """
    # 已知的需要替换的前缀
    prefix_mapping = {
        "CN_Programs": "CN Programs",
        "JP_Programs": "JP Programs",
        "KR_Programs": "KR Programs",
        "US_Programs": "US Programs",
    }

    for old_prefix, new_prefix in prefix_mapping.items():
        if gdrive_path.startswith(old_prefix):
            return new_prefix + gdrive_path[len(old_prefix):]

    return gdrive_path


def _get_root_folder_id(gdrive_path: str) -> Optional[str]:
    """从 gdrive_path 中提取根目录名称并返回对应的 folder ID。

    例如: "CN Programs/KR085..." 或 "CN_Programs/KR085..." -> 返回 CN Programs 的 folder ID
    """
    if not gdrive_path:
        return None

    # 获取路径的第一部分（根目录名称）
    parts = gdrive_path.replace("\\", "/").strip("/").split("/")
    if not parts:
        return None

    root_name = parts[0]

    # 标准化根目录名称（处理下划线和空格的差异）
    # 将空格替换为下划线以匹配配置中的 label
    root_name_normalized = root_name.replace(" ", "_")

    # 从配置中查找对应的 folder ID
    for label, folder_id in settings.pipeline_gdrive_roots:
        # label 使用下划线（如 CN_Programs）
        if label == root_name_normalized or label.replace("_", " ") == root_name:
            _log(f"找到根目录 '{root_name}' 的 folder ID: {folder_id}")
            return folder_id

    _log(f"警告: 未找到根目录 '{root_name}' 的配置")
    return None


def _get_relative_path_from_root(gdrive_path: str) -> str:
    """从 gdrive_path 中提取相对于根目录的路径。

    例如: "CN Programs/KR085P01S01_xxx" -> "KR085P01S01_xxx"
    """
    if not gdrive_path:
        return ""

    parts = gdrive_path.replace("\\", "/").strip("/").split("/", 1)
    if len(parts) > 1:
        return parts[1]
    return ""


def _write_rclone_config(
    drive_token: Dict[str, str],
    *,
    temp_dir: Path,
) -> Path:
    """Generate a temporary rclone configuration file."""
    config_path = temp_dir / "rclone.conf"

    drive_section = [
        "[my-drive]",
        "type = drive",
        "scope = drive",
        "use_trash = false",
        f"client_id = {settings.google_oauth_client_id}",
        f"client_secret = {settings.google_oauth_client_secret}",
        f"token = {json.dumps(drive_token)}",
        "",
    ]

    gcs_section: List[str] = ["[my-gcs-bucket]", "type = google cloud storage", "bucket_policy_only = true"]
    if settings.app_env == "development":
        creds_path = settings.google_application_credentials
        if not creds_path:
            raise RuntimeError("开发环境需要 GOOGLE_APPLICATION_CREDENTIALS 指向 service account JSON")
        gcs_section.append(f"service_account_file = {creds_path}")
    else:
        gcs_section.append("env_auth = true")
    gcs_section.append("")

    config_path.write_text("\n".join(drive_section + gcs_section), encoding="utf-8")
    return config_path


def _escape_filter_component(component: str) -> str:
    """Escape glob special characters so rclone interprets literal names."""
    # 逐个字符处理，避免 replace 影响已转义的部分
    # 例如 "[Final]" 应该变成 "[[]Final[]]"
    result = []
    for char in component:
        if char == "[":
            result.append("[[]")
        elif char == "]":
            result.append("[]]")
        elif char == "?":
            result.append(r"\?")
        elif char == "*":
            result.append(r"\*")
        else:
            result.append(char)
    return "".join(result)


def _normalize_relative_path(folder: str, drama_root: str) -> str:
    """Convert absolute folder path to relative path under the drama root."""
    folder_norm = folder.replace("\\", "/").strip("/")
    root_norm = (drama_root or "").replace("\\", "/").strip("/")
    
    # 如果 folder 以 root 开头，直接提取相对路径
    if root_norm and folder_norm.startswith(root_norm):
        return folder_norm[len(root_norm) :].strip("/")
    
    # 如果 folder 不包含 root 的前缀，尝试匹配 root 的最后一部分（剧集名称）
    # 例如：root = "US Programs/US044P01S01_..."，folder = "US044P01S01_.../episodes/..."
    if root_norm:
        root_parts = [p for p in root_norm.split("/") if p]
        if root_parts:
            drama_name = root_parts[-1]  # 获取剧集名称（root 的最后一部分）
            # 检查 folder 是否以剧集名称开头
            if folder_norm.startswith(drama_name + "/") or folder_norm == drama_name:
                # 提取剧集名称之后的部分
                if folder_norm == drama_name:
                    return ""
                return folder_norm[len(drama_name) :].strip("/")
            # 如果 folder 已经以剧集名称开头，但前面还有其他路径，尝试匹配
            # 例如：folder = "US044P01S01_.../episodes/..."，但 root = "US Programs/US044P01S01_..."
            for i in range(len(root_parts) - 1, -1, -1):
                # 从后往前匹配，找到第一个匹配的部分
                partial_root = "/".join(root_parts[i:])
                if folder_norm.startswith(partial_root + "/") or folder_norm == partial_root:
                    if folder_norm == partial_root:
                        return ""
                    return folder_norm[len(partial_root) :].strip("/")
    
    return folder_norm


def _compile_filter_rules(include_folders: List[str], drama_root: str) -> List[str]:
    rules: List[str] = []
    for folder in include_folders:
        if not folder:
            continue
        relative_path = _normalize_relative_path(folder, drama_root)
        print(f"🔍 [DEBUG] Filter rule generation:")
        print(f"   Original folder: {folder}")
        print(f"   Drama root: {drama_root}")
        print(f"   Normalized relative_path: {relative_path}")
        parts = [part for part in relative_path.split("/") if part]
        if not parts:
            rules.append("+ /**")
            continue
        escaped = "/".join(_escape_filter_component(part) for part in parts)
        filter_rule = f"+ /{escaped}/**"
        print(f"   Generated filter rule: {filter_rule}")
        rules.append(filter_rule)
    return rules


def _build_filter_file(
    include_folders: List[str],
    drama_root: str,
    temp_dir: Path,
) -> Optional[Path]:
    """Create an rclone filter file using precise relative paths."""
    if not include_folders:
        return None

    rules = _compile_filter_rules(include_folders, drama_root)
    if not rules:
        return None

    rules.append("- **")
    filter_path = temp_dir / "transfer.filter"
    print("🔍 [DEBUG] Rclone Filter Rules:\n" + "\n".join(rules))
    filter_path.write_text("\n".join(rules), encoding="utf-8")
    return filter_path


def _update_progress(doc_ref, *, status: str, progress: str) -> None:
    doc_ref.update(
        {
            "status": status,
            "progress": progress,
            "updated_at": SERVER_TIMESTAMP,
        }
    )


def _finalize_success(doc_ref, storage_client, bucket_name: str, drama_name: str) -> None:
    blob_path = f"{drama_name}/_PROCESS_NOW.txt"
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_string("", content_type="text/plain")
    doc_ref.update(
        {
            "status": "COMPLETE",
            "progress": "传输完成，等待压制",
            "stage": 1,
            "transfer_completed": True,
            "last_event": {
                "type": "TRANSFER_COMPLETED",
                "timestamp": SERVER_TIMESTAMP,
            },
            "updated_at": SERVER_TIMESTAMP,
        }
    )


def _mark_failure(doc_ref, message: str) -> None:
    doc_ref.update(
        {
            "status": "FAILED",
            "progress": message[:500],
            "last_event": {
                "type": "TRANSFER_FAILED",
                "error": message[:500],
                "timestamp": SERVER_TIMESTAMP,
            },
            "updated_at": SERVER_TIMESTAMP,
        }
    )


def run_worker() -> None:
    init_firestore()
    firestore_client = get_firestore_client()
    storage_client = storage.Client()

    job_id = _require_env("JOB_ID")
    token_ref = _require_env("REFRESH_TOKEN_REF")
    rclone_path = os.environ.get("RCLONE_PATH", "rclone")

    _log(f"开始执行 Job {job_id}，环境：{settings.app_env}")
    job_ref = firestore_client.collection("pipeline_jobs").document(job_id)
    snapshot = job_ref.get()
    if not snapshot.exists:
        raise RuntimeError("指定 job_id 的 Firestore 文档不存在")
    job_data = snapshot.to_dict() or {}

    include_folders = job_data.get("include_folders") or []
    gdrive_path = job_data.get("gdrive_path")
    drama_name = job_data.get("drama_name") or Path(gdrive_path or "").name
    bucket_name = job_data.get("gcs_source_bucket") or settings.pipeline_gcs_source_bucket

    if not gdrive_path:
        raise RuntimeError("job 文档缺少 gdrive_path")

    # 修正路径：将配置中的下划线替换为空格，匹配 Google Drive 真实文件夹名
    # 例如: CN_Programs/KR085... -> CN Programs/KR085...
    gdrive_path_fixed = _fix_gdrive_path(gdrive_path)
    _log(f"原始路径: {gdrive_path}")
    _log(f"修正路径: {gdrive_path_fixed}")

    # 获取根目录的 folder ID（用于支持共享驱动器）
    root_folder_id = _get_root_folder_id(gdrive_path_fixed)
    # 获取相对于根目录的路径
    relative_path = _get_relative_path_from_root(gdrive_path_fixed)
    _log(f"根目录 folder ID: {root_folder_id}")
    _log(f"相对路径: {relative_path}")

    refresh_token = retrieve_refresh_token(token_ref)
    drive_token = _exchange_refresh_token(refresh_token)

    with tempfile.TemporaryDirectory(prefix="transfer-worker-") as tmpdir:
        temp_dir = Path(tmpdir)
        config_path = _write_rclone_config(drive_token, temp_dir=temp_dir)
        filter_file = _build_filter_file(include_folders, gdrive_path_fixed or drama_name, temp_dir)

        # 构建 rclone 源路径
        # 如果有 root_folder_id，使用相对路径；否则使用完整路径
        if root_folder_id:
            rclone_source = f"my-drive:{relative_path}"
        else:
            rclone_source = f"my-drive:{gdrive_path_fixed}"

        cmd = [
            rclone_path,
            "copy",
            rclone_source,
            f"my-gcs-bucket:{bucket_name}/{drama_name}",
            "--config",
            str(config_path),
            "--drive-shared-with-me",
            "--transfers=8",
            "--checkers=8",
            "-P",
        ]

        # 如果有根目录 folder ID，添加参数以支持共享驱动器
        if root_folder_id:
            cmd.extend(["--drive-root-folder-id", root_folder_id])

        if filter_file:
            cmd.extend(["--filter-from", str(filter_file)])

        if filter_file and filter_file.exists():
            _log("🔍 [DEBUG] Rclone Filter Content:\n" + filter_file.read_text(encoding="utf-8"))

        _log("执行命令：" + " ".join(cmd))
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        last_update = 0.0
        try:
            _update_progress(job_ref, status="TRANSFERRING", progress="rclone 已启动")
            assert process.stdout is not None
            for line in process.stdout:
                clean_line = line.strip()
                if not clean_line:
                    continue
                print(clean_line, flush=True)
                match = PROGRESS_REGEX.search(clean_line)
                now = time.time()
                if match and (now - last_update) >= FILTER_COOLDOWN_SECONDS:
                    percent = match.group(1)
                    _update_progress(
                        job_ref,
                        status="TRANSFERRING",
                        progress=f"已传输 {percent}% | {clean_line}",
                    )
                    last_update = now

            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"rclone 退出码非 0：{return_code}")

            _finalize_success(job_ref, storage_client, bucket_name, drama_name)
            _log("传输完成，_PROCESS_NOW.txt 已创建")
        except Exception as exc:
            _mark_failure(job_ref, str(exc))
            raise
        finally:
            try:
                process.kill()
            except Exception:
                pass

        # Ensure temporary config/filter removed (TemporaryDirectory handles cleanup)
        if config_path.exists():
            try:
                config_path.unlink()
            except OSError:
                pass
        if filter_file and filter_file.exists():
            try:
                filter_file.unlink()
            except OSError:
                pass


def main() -> None:
    try:
        run_worker()
    except Exception as exc:
        _log(f"❌ Worker 执行失败：{exc}")
        raise


if __name__ == "__main__":
    main()


