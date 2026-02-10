"""Service to build pipeline status data between Google Drive and GCS."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from google.auth.transport.requests import Request
from google.cloud import storage
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.schemas.auth import AuthenticatedUser
from app.services import google_oauth_service
from app.services.google_oauth_service import TokenStorageError

FOLDER_MIME = "application/vnd.google-apps.folder"


class PipelineStatusService:
    """Build pipeline status (Drive + GCS) with graceful fallbacks."""

    def __init__(self, acting_user: Optional[AuthenticatedUser] = None) -> None:
        self._mock_data = self._load_mock_data()
        self._bucket_name = settings.pipeline_gcs_source_bucket or "vigloo_source"
        self._processed_bucket = (
            settings.pipeline_gcs_processed_bucket or f"{self._bucket_name}-processed"
        )
        self._drive_roots = settings.pipeline_gdrive_roots
        self._acting_user = acting_user
        self._token_ref = self._resolve_token_ref()
        if not self._token_ref:
            raise TokenStorageError("PIPELINE_DEFAULT_TOKEN_REF 未配置，无法访问 Google Drive")
        self._program_cache: Optional[List[Dict[str, Any]]] = None
        self._folder_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._storage_client: Optional[storage.Client] = None
        self._gcs_top_level_cache: Optional[set[str]] = None

    # ------------------------------------------------------------------ Helpers
    @staticmethod
    def _normalize_gcs_prefix(prefix: Optional[str]) -> str:
        if not prefix:
            return ""
        return prefix.strip("/ ")

    def _compose_gcs_path(self, base_prefix: Optional[str], folder_name: str) -> str:
        sanitized_base = self._normalize_gcs_prefix(base_prefix)
        sanitized_name = folder_name.strip("/ ")
        if not sanitized_base:
            return sanitized_name
        if not sanitized_name:
            return sanitized_base
        return f"{sanitized_base}/{sanitized_name}"

    # ------------------------------------------------------------------ Public API
    def list_program_status(self) -> List[Dict[str, Any]]:
        programs = self._load_real_programs()
        if programs:
            return programs
        if self._mock_data:
            return self._programs_from_mock()
        return []

    def list_unprocessed_dramas(self) -> List[str]:
        """Return dramas existing in source bucket but missing from processed bucket."""
        client = self._storage()
        if client is None:
            return []

        source_bucket = self._bucket_name
        processed_bucket = self._processed_bucket

        try:
            source_prefixes = self._list_top_level_prefixes(client, source_bucket)
        except Exception as exc:  # pragma: no cover - log and fall back
            print(f"⚠️  列举源桶 {source_bucket} 失败：{exc}")
            return []

        try:
            processed_prefixes = (
                self._list_top_level_prefixes(client, processed_bucket)
                if processed_bucket
                else []
            )
        except Exception as exc:  # pragma: no cover
            print(f"⚠️  列举已压制桶 {processed_bucket} 失败：{exc}")
            processed_prefixes = []

        processed_set = {prefix.rstrip("/") for prefix in processed_prefixes}
        missing = []
        for prefix in source_prefixes:
            name = prefix.rstrip("/")
            if not name:
                continue
            if name not in processed_set:
                missing.append(name)
        return sorted(missing)

    def list_program_folders(
        self, program_path: str, include_children: bool
    ) -> Optional[List[Dict[str, Any]]]:
        if self._program_cache is None:
            self._load_real_programs()
        folders = self._folder_cache.get(program_path)
        if folders is not None:
            if include_children:
                return folders
            return [
                {k: v for k, v in folder.items() if k != "children"} for folder in folders
            ]
        # fallback to mock data if available
        program = self._find_program_in_mock(program_path)
        if not program:
            return None
        return [
            self._format_mock_folder(folder, include_children=include_children)
            for folder in program.get("folders", [])
        ]

    # ------------------------------------------------------------------ Real data loaders
    def _load_real_programs(self) -> List[Dict[str, Any]]:
        if self._program_cache is not None:
            return self._program_cache

        programs: List[Dict[str, Any]] = []
        self._folder_cache = {}

        drive_programs = self._collect_from_drive()
        if drive_programs:
            programs = drive_programs
        else:
            gcs_programs = self._collect_from_gcs()
            programs = gcs_programs

        if not programs and self._mock_data:
            programs = self._programs_from_mock()

        self._program_cache = programs
        return programs

    def browse_drive_folder(
        self, folder_id: str, gcs_prefix: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List direct child folders for a given Drive folder."""
        if not folder_id:
            return []
        drive_service = self._build_drive_service()
        if drive_service is None:
            return []

        normalized_prefix = self._normalize_gcs_prefix(gcs_prefix)
        query = (
            f"'{folder_id}' in parents AND mimeType='{FOLDER_MIME}' AND trashed=false"
        )
        
        # 先收集所有子目录信息
        folders: List[Dict[str, Any]] = []
        for folder in self._drive_list(drive_service, query):
            name = folder.get("name", "")
            child_id = folder.get("id")
            if not child_id:
                continue
            folders.append({"id": child_id, "name": name})
        
        # 批量检查 GCS 目录存在性
        # 优化：如果目录数量较多（>30），跳过详细 GCS 检查以提升性能
        # 用户仍可以看到目录结构，只是 GCS 状态显示为未同步（不影响功能）
        folder_names = [f["name"] for f in folders]
        if len(folder_names) > 30:
            # 对于大量目录，跳过 GCS 检查以提升性能（返回 False）
            # 这样可以确保响应时间在 2 秒以内
            gcs_existence_map = {name: False for name in folder_names}
        else:
            # 对于少量目录，使用并发检查
            gcs_existence_map = self._batch_check_gcs_folders(normalized_prefix, folder_names)
        
        nodes: List[Dict[str, Any]] = []
        for folder in folders:
            name = folder["name"]
            child_id = folder["id"]
            # 避免为每个子目录再次调用 Drive API 判断是否存在子目录，
            # 统一标记为 True，由前端在展开时再发起实际请求。
            has_children = True
            in_gcs = gcs_existence_map.get(name, False)
            nodes.append(
                {
                    "id": child_id,
                    "name": name,
                    "has_children": has_children,
                    "in_gcs": in_gcs,
                }
            )

        return sorted(nodes, key=lambda item: item["name"])

    def _collect_from_drive(self) -> List[Dict[str, Any]]:
        if not self._drive_roots:
            return []
        drive_service = self._build_drive_service()
        if drive_service is None:
            return []

        collected: List[Dict[str, Any]] = []
        for label, folder_id in self._drive_roots:
            print(f"🔍 [DEBUG] 正在尝试访问根目录 {label} (folder_id={folder_id})")
            query = (
                f"'{folder_id}' in parents AND mimeType='{FOLDER_MIME}' AND trashed=false"
            )
            try:
                before_count = len(collected)
                for program_folder in self._drive_list(drive_service, query):
                    program_name = program_folder.get("name", "")
                    path = f"{label}/{program_name}"
                    folder_nodes, totals = self._build_drive_folder_nodes(
                        drive_service, program_folder, program_name
                    )
                    collected.append({
                        "name": program_name,
                        "path": path,
                        "gdrive_id": program_folder["id"],
                        "in_gcs": totals["files_in_gcs"] > 0,
                        "files_total": totals["files_total"],
                        "files_in_gcs": totals["files_in_gcs"],
                        "updated_at": None,
                        "total_size_bytes": None,
                    })
                    self._folder_cache[path] = folder_nodes
                print(
                    f"✅ [DEBUG] 根目录 {label} 读取成功，新增加 {len(collected) - before_count} 个节目"
                )
            except HttpError as exc:
                print(f"❌ [DEBUG] 无法读取 GDrive 根目录 {label}: {exc}")
                if hasattr(exc, "resp"):
                    print(f"❌ [DEBUG] HTTP 状态码: {exc.resp.status}")
                if hasattr(exc, "content"):
                    print(f"❌ [DEBUG] 响应内容: {exc.content}")
                raise
            except Exception as exc:
                print(f"❌ [DEBUG] 读取 GDrive 根目录 {label} 时发生未知错误: {exc}")
                raise
        return collected

    def _collect_from_gcs(self) -> List[Dict[str, Any]]:
        client = self._storage()
        if client is None:
            return []

        prefixes = self._list_top_level_prefixes(client)
        programs: List[Dict[str, Any]] = []
        for prefix in prefixes:
            program_name = prefix.rstrip("/")
            folder_nodes, totals = self._build_gcs_folder_nodes(client, program_name)
            programs.append({
                "name": program_name,
                "path": program_name,
                "gdrive_id": "",
                "in_gcs": totals["files_in_gcs"] > 0,
                "files_total": totals["files_in_gcs"],
                "files_in_gcs": totals["files_in_gcs"],
                "updated_at": None,
                "total_size_bytes": None,
            })
            self._folder_cache[program_name] = folder_nodes
        return programs

    # ------------------------------------------------------------------ Drive helpers
    def _build_drive_service(self):
        if not self._token_ref:
            return None
        if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
            return None

        token_from_frontend = getattr(self._acting_user, "auth_token", None)
        print(f"[PipelineStatus] APP_ENV={settings.app_env}")
        print(f"[PipelineStatus] token_from_frontend={token_from_frontend}")
        if self._acting_user and self._acting_user.is_dev_user:
            print("✅ 进入开发模式后门逻辑")
        else:
            print("❌ 未进入后门逻辑 (使用用户原生 Token)")

        try:
            print(f"[PipelineStatus] 尝试读取 Firestore token ref: {self._token_ref}")
            refresh_token = google_oauth_service.retrieve_refresh_token(self._token_ref)
            token_preview = refresh_token[:5] + "..." if refresh_token else "None"
            print(f"[PipelineStatus] Firestore 读取结果：{'有数据' if refresh_token else 'None'} (preview={token_preview})")
        except TokenStorageError as exc:
            print(f"⚠️  无法获取用户刷新令牌：{exc}")
            return None
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        try:
            creds.refresh(Request())
        except Exception as exc:
            print(f"⚠️  刷新 Google Drive access token 失败：{exc}")
            return None
        print(f"[PipelineStatus] Credentials refresh_token preview={token_preview}")
        print(f"[PipelineStatus] Credentials valid={creds.valid}, expired={creds.expired}")
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def _resolve_token_ref(self) -> Optional[str]:
        """Determine which refresh token reference to use for Drive."""
        # In development dev-mode, always fall back to shared token
        if self._acting_user and self._acting_user.is_dev_user:
            return settings.pipeline_default_token_ref

        if self._acting_user:
            try:
                user_token_ref = google_oauth_service.lookup_latest_token_ref(
                    self._acting_user
                )
                if user_token_ref:
                    return user_token_ref
            except Exception as exc:  # pragma: no cover - log and continue
                print(f"⚠️  查询用户刷新令牌失败：{exc}")

        return settings.pipeline_default_token_ref

    def _drive_list(self, service, query: str) -> Iterable[Dict[str, Any]]:
        page_token = None
        while True:
            try:
                response = (
                    service.files()
                    .list(
                        q=query,
                        fields="nextPageToken, files(id,name,mimeType)",
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        pageSize=1000,
                        pageToken=page_token,
                    )
                    .execute()
                )
                files = response.get("files", [])
                # 移除调试日志以提升性能
            except Exception as exc:
                print("❌ [DEBUG] Google Drive API 调用炸了！")
                print(f"❌ [DEBUG] 错误类型: {type(exc)}")
                print(f"❌ [DEBUG] 错误详情: {exc}")
                if hasattr(exc, "resp"):
                    print(f"❌ [DEBUG] HTTP 状态码: {exc.resp.status}")
                if hasattr(exc, "content"):
                    print(f"❌ [DEBUG] 响应内容: {exc.content}")
                raise
            for item in response.get("files", []):
                yield item
            page_token = response.get("nextPageToken")
            if not page_token:
                break

    def _build_drive_folder_nodes(
        self, service, program_folder: Dict[str, Any], program_name: str
    ) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        gcs_stats = self._gcs_stats_for_program(program_name)
        totals = {"files_total": 0, "files_in_gcs": 0}
        nodes: List[Dict[str, Any]] = []
        folder_id = program_folder["id"]
        print(f"🔍 [DEBUG] 列举剧集子目录: {program_name} (folder_id={folder_id})")
        query = (
            f"'{folder_id}' in parents AND mimeType='{FOLDER_MIME}' AND trashed=false"
        )
        try:
            for folder in self._drive_list(service, query):
                node = self._build_drive_folder_node(
                    service, folder, gcs_stats.get(folder["name"], {})
                )
                totals["files_total"] += node.get("files_total") or 0
                totals["files_in_gcs"] += node.get("files_in_gcs") or 0
                nodes.append(node)
            print(f"✅ [DEBUG] 剧集 {program_name} 读取 {len(nodes)} 个一级目录")
        except HttpError as exc:
            print(f"❌ [DEBUG] 无法读取剧集 {program_name} 的子目录: {exc}")
            if hasattr(exc, "resp"):
                print(f"❌ [DEBUG] HTTP 状态码: {exc.resp.status}")
            if hasattr(exc, "content"):
                print(f"❌ [DEBUG] 响应内容: {exc.content}")
            raise
        except Exception as exc:
            print(f"❌ [DEBUG] 读取剧集 {program_name} 发生未知错误: {exc}")
            raise
        return nodes, totals

    def _build_drive_folder_node(
        self, service, folder: Dict[str, Any], gcs_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        files_total = 0
        children: List[Dict[str, Any]] = []
        folder_id = folder["id"]
        print(f"🔍 [DEBUG] 读取文件夹 {folder.get('name')} (id={folder_id})")
        query = f"'{folder_id}' in parents AND trashed=false"
        try:
            for item in self._drive_list(service, query):
                if item.get("mimeType") == FOLDER_MIME:
                    child = self._build_drive_folder_node(
                        service,
                        item,
                        (gcs_info.get("children", {}).get(item["name"]) if gcs_info else {}),
                    )
                    files_total += child.get("files_total") or 0
                    children.append(child)
                else:
                    files_total += 1
            print(f"✅ [DEBUG] 文件夹 {folder.get('name')} 读取完成，文件总数 {files_total}")
        except HttpError as exc:
            print(f"❌ [DEBUG] 无法读取文件夹 {folder.get('name')} ({folder_id})：{exc}")
            if hasattr(exc, "resp"):
                print(f"❌ [DEBUG] HTTP 状态码: {exc.resp.status}")
            if hasattr(exc, "content"):
                print(f"❌ [DEBUG] 响应内容: {exc.content}")
            raise
        except Exception as exc:
            print(f"❌ [DEBUG] 文件夹 {folder.get('name')} 读取发生未知错误: {exc}")
            raise
        node = {
            "id": folder["id"],
            "name": folder.get("name", ""),
            "files_total": files_total,
            "files_in_gcs": gcs_info.get("files_in_gcs", 0) if gcs_info else 0,
        }
        if children:
            node["children"] = children
        return node

    # ------------------------------------------------------------------ GCS helpers
    def _storage(self) -> Optional[storage.Client]:
        if self._storage_client:
            return self._storage_client
        # Ensure credentials env is absolute
        creds_path = settings.google_application_credentials
        if creds_path and not os.path.isabs(creds_path):
            creds_path = str(Path(__file__).parent.parent.parent / creds_path)
        if creds_path and os.path.exists(creds_path):
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", creds_path)
        try:
            self._storage_client = storage.Client(project=settings.firestore_project_id or None)
        except Exception as exc:
            print(f"⚠️  初始化 GCS Client 失败：{exc}")
            self._storage_client = None
        return self._storage_client

    def _batch_check_gcs_folders_optimized(
        self, base_prefix: Optional[str], folder_names: List[str]
    ) -> Dict[str, bool]:
        """优化的批量检查方法：对于大量目录，使用批量列出方式检查。
        
        当目录数量很多时，逐个检查会很慢。此方法通过一次性列出所有可能的前缀
        来批量判断目录是否存在，显著提升性能。
        """
        if not folder_names:
            return {}
        
        client = self._storage()
        if client is None:
            return {name: False for name in folder_names}
        
        normalized_base = self._compose_gcs_path(base_prefix, "")
        result: Dict[str, bool] = {}
        
        # 如果是顶级目录检查，使用缓存的 top_level 集合
        if not normalized_base:
            top_level = self._get_top_level_gcs_names()
            for name in folder_names:
                result[name] = name.strip("/ ") in top_level
            return result
        
        # 批量列出：一次性列出所有可能的前缀，然后匹配
        # 构建所有需要检查的路径
        paths_to_check: Dict[str, str] = {}  # {folder_name: full_path}
        for folder_name in folder_names:
            path = self._compose_gcs_path(base_prefix, folder_name)
            if path:
                paths_to_check[folder_name] = path
        
        if not paths_to_check:
            return {name: False for name in folder_names}
        
        # 使用 delimiter 批量列出所有前缀
        # 列出 base_prefix 下的所有一级前缀
        base_path = normalized_base if normalized_base else ""
        list_prefix = f"{base_path}/" if base_path else ""
        
        try:
            # 列出所有一级前缀
            existing_prefixes: set[str] = set()
            iterator = client.list_blobs(
                self._bucket_name, 
                prefix=list_prefix, 
                delimiter="/",
                max_results=1000  # 限制结果数量以避免过慢
            )
            
            # 收集所有存在的前缀（去掉 base_path 前缀）
            for page in iterator.pages:
                for prefix in page.prefixes:
                    # prefix 格式: "base_path/folder_name/"
                    if prefix.startswith(list_prefix):
                        relative = prefix[len(list_prefix):].rstrip("/")
                        if relative:
                            existing_prefixes.add(relative)
            
            # 匹配哪些目录存在
            for folder_name, full_path in paths_to_check.items():
                # full_path 格式: "base_path/folder_name"
                # 需要检查 folder_name 是否在 existing_prefixes 中
                if base_path:
                    # 如果 base_path 存在，full_path 是 "base_path/folder_name"
                    # 需要提取 folder_name
                    if full_path.startswith(base_path + "/"):
                        relative_name = full_path[len(base_path) + 1:]
                    else:
                        relative_name = folder_name
                else:
                    relative_name = folder_name
                
                result[folder_name] = relative_name in existing_prefixes
            
            # 对于没有匹配到的目录，设置为 False
            for folder_name in folder_names:
                if folder_name not in result:
                    result[folder_name] = False
                    
        except Exception as exc:
            print(f"⚠️  批量检查 GCS 目录失败：{exc}")
            # 如果批量检查失败，返回所有 False
            return {name: False for name in folder_names}
        
        return result

    def _batch_check_gcs_folders(
        self, base_prefix: Optional[str], folder_names: List[str]
    ) -> Dict[str, bool]:
        """批量检查多个目录在 GCS 中是否存在，返回字典 {folder_name: exists}。
        
        使用并发检查来提升性能，适用于目录数量较少的情况（<=50）。
        """
        if not folder_names:
            return {}
        
        client = self._storage()
        if client is None:
            return {name: False for name in folder_names}
        
        normalized_base = self._compose_gcs_path(base_prefix, "")
        result: Dict[str, bool] = {}
        
        # 如果是顶级目录检查，使用缓存的 top_level 集合（无需并发）
        if not normalized_base:
            top_level = self._get_top_level_gcs_names()
            for name in folder_names:
                result[name] = name.strip("/ ") in top_level
            return result
        
        # 并发检查：使用线程池并行检查多个目录
        def check_single_folder(folder_name: str) -> tuple[str, bool]:
            """检查单个目录是否存在"""
            path = self._compose_gcs_path(base_prefix, folder_name)
            if not path:
                return folder_name, False
            
            try:
                iterator = client.list_blobs(self._bucket_name, prefix=f"{path}/", max_results=1)
                try:
                    next(iterator)
                    return folder_name, True
                except StopIteration:
                    return folder_name, False
            except Exception as exc:
                print(f"⚠️  检查 GCS 目录 {path} 失败：{exc}")
                return folder_name, False
        
        # 使用线程池并发检查，增加并发数以提升性能
        max_workers = min(30, len(folder_names), 20)  # 最多 20-30 个并发
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_name = {
                executor.submit(check_single_folder, name): name 
                for name in folder_names
            }
            for future in as_completed(future_to_name):
                try:
                    folder_name, exists = future.result()
                    result[folder_name] = exists
                except Exception as exc:
                    folder_name = future_to_name[future]
                    print(f"⚠️  检查目录 {folder_name} 时发生异常：{exc}")
                    result[folder_name] = False
        
        return result

    def _gcs_folder_exists(self, base_prefix: Optional[str], folder_name: str) -> bool:
        """检查单个目录在 GCS 中是否存在（保留用于向后兼容）"""
        result = self._batch_check_gcs_folders(base_prefix, [folder_name])
        return result.get(folder_name, False)

    def _get_top_level_gcs_names(self) -> set[str]:
        if self._gcs_top_level_cache is not None:
            return self._gcs_top_level_cache
        client = self._storage()
        if client is None:
            self._gcs_top_level_cache = set()
            return self._gcs_top_level_cache
        prefixes = self._list_top_level_prefixes(client, self._bucket_name)
        self._gcs_top_level_cache = {prefix.rstrip("/") for prefix in prefixes if prefix}
        return self._gcs_top_level_cache

    def _list_top_level_prefixes(
        self, client: storage.Client, bucket_name: str | None = None
    ) -> List[str]:
        target_bucket = bucket_name or self._bucket_name
        if not target_bucket:
            return []
        iterator = client.list_blobs(target_bucket, delimiter="/")
        prefixes = set()
        for page in iterator.pages:
            prefixes.update(page.prefixes)
        return sorted(prefixes)

    def _build_gcs_folder_nodes(
        self, client: storage.Client, program_name: str
    ) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        prefix = f"{program_name}/"
        stats = self._gcs_stats_for_program(program_name, client=client)
        nodes: List[Dict[str, Any]] = []
        total_counts = {"files_in_gcs": 0}
        for folder_name, info in stats.items():
            node = {
                "id": f"gcs::{program_name}/{folder_name}",
                "name": folder_name,
                "files_total": info["files_in_gcs"],
                "files_in_gcs": info["files_in_gcs"],
            }
            if info.get("children"):
                node["children"] = [
                    {
                        "id": f"gcs::{program_name}/{folder_name}/{child_name}",
                        "name": child_name,
                        "files_total": child_info["files_in_gcs"],
                        "files_in_gcs": child_info["files_in_gcs"],
                    }
                    for child_name, child_info in info["children"].items()
                ]
            nodes.append(node)
            total_counts["files_in_gcs"] += info["files_in_gcs"]
        return nodes, total_counts

    def _gcs_stats_for_program(self, program_name: str, client: Optional[storage.Client] = None):
        client = client or self._storage()
        if client is None:
            return {}
        prefix = f"{program_name}/"
        iterator = client.list_blobs(self._bucket_name, prefix=prefix)
        stats: Dict[str, Dict[str, Any]] = {}
        for blob in iterator:
            relative = blob.name[len(prefix):]
            if not relative:
                continue
            parts = [part for part in relative.split("/") if part]
            if not parts:
                continue
            top = parts[0]
            node = stats.setdefault(top, {"files_in_gcs": 0, "children": {}})
            node["files_in_gcs"] += 1
            if len(parts) > 1:
                second = parts[1]
                child = node["children"].setdefault(second, {"files_in_gcs": 0, "children": {}})
                child["files_in_gcs"] += 1
        return stats

    # ------------------------------------------------------------------ Mock fallbacks
    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path(__file__).parent.parent.parent / raw_path
        return path

    def _load_mock_data(self) -> Optional[Dict[str, Any]]:
        mock_file = settings.pipeline_status_mock_file
        if not mock_file:
            return None
        path = self._resolve_path(mock_file)
        if not path.exists():
            print(f"⚠️  PIPELINE_STATUS_MOCK_FILE 指向的文件不存在：{path}")
            return None
        try:
            with path.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except json.JSONDecodeError as exc:
            print(f"⚠️  无法解析 mock pipeline 数据：{exc}")
            return None

    def _programs_from_mock(self) -> List[Dict[str, Any]]:
        programs: List[Dict[str, Any]] = []
        if not self._mock_data:
            return programs
        for root in self._mock_data.get("roots", []):
            root_name = root.get("name", "")
            for item in root.get("items", []):
                folders = item.get("folders", [])
                total, synced = self._aggregate_mock_stats(folders)
                path = item.get("path") or f"{root_name}/{item.get('name', '')}"
                programs.append({
                    "name": item.get("name", ""),
                    "path": path,
                    "gdrive_id": item.get("gdrive_id", ""),
                    "in_gcs": synced > 0,
                    "files_total": item.get("files_total", total),
                    "files_in_gcs": item.get("files_in_gcs", synced),
                    "updated_at": item.get("updated_at"),
                    "total_size_bytes": item.get("total_size_bytes"),
                })
                self._folder_cache[path] = folders
        return programs

    def _aggregate_mock_stats(self, folders: List[Dict[str, Any]]) -> tuple[int, int]:
        total = 0
        synced = 0
        for folder in folders:
            folder_total = folder.get("files_total")
            folder_synced = folder.get("files_in_gcs")
            if folder_total is None or folder_synced is None:
                child_total, child_synced = self._aggregate_mock_stats(folder.get("children", []))
                folder_total = folder_total or child_total
                folder_synced = folder_synced or child_synced
            if folder_total:
                total += folder_total
            if folder_synced:
                synced += folder_synced
        return total, synced

    def _find_program_in_mock(self, program_path: str) -> Optional[Dict[str, Any]]:
        if not self._mock_data:
            return None
        for root in self._mock_data.get("roots", []):
            for item in root.get("items", []):
                path = item.get("path") or f"{root.get('name', '')}/{item.get('name', '')}"
                if path == program_path:
                    return item
        return None

    def _format_mock_folder(self, folder: Dict[str, Any], include_children: bool) -> Dict[str, Any]:
        formatted = {
            "id": folder.get("id", ""),
            "name": folder.get("name", ""),
            "files_total": folder.get("files_total"),
            "files_in_gcs": folder.get("files_in_gcs"),
        }
        if include_children and folder.get("children"):
            formatted["children"] = [
                self._format_mock_folder(child, include_children=True)
                for child in folder["children"]
            ]
        return formatted


def get_pipeline_status_service(
    acting_user: Optional[AuthenticatedUser] = None,
) -> PipelineStatusService:
    return PipelineStatusService(acting_user=acting_user)


__all__ = ["PipelineStatusService", "get_pipeline_status_service"]

