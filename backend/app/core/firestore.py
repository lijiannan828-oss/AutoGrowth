"""Firestore client initialization and helpers."""

from __future__ import annotations

import os
from typing import Optional

from google.cloud import firestore
from google.api_core.client_options import ClientOptions

from app.core.config import settings

_firestore_client: Optional[firestore.Client] = None


def init_firestore() -> Optional[firestore.Client]:
    """Initialize global Firestore client if project is configured."""
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    project_id = settings.resolved_firestore_project
    if not project_id:
        print("[WARN] Firestore project ID 未配置，跳过 Firestore 初始化")
        return None

    client_options: ClientOptions | None = None

    # Ensure ADC credentials are available similar to database setup
    creds_path = settings.google_application_credentials
    if creds_path:
        if not os.path.isabs(creds_path):
            from pathlib import Path

            creds_path = str(Path(__file__).parent.parent.parent / creds_path)
        if os.path.exists(creds_path):
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", creds_path)

    # Allow developers to point to emulator via env
    # Only set emulator host if it's a non-empty string
    emulator_host = settings.firestore_emulator_host
    if not emulator_host or not emulator_host.strip():
        # Clear empty emulator host from environment if present
        if "FIRESTORE_EMULATOR_HOST" in os.environ and not os.environ["FIRESTORE_EMULATOR_HOST"].strip():
            del os.environ["FIRESTORE_EMULATOR_HOST"]
        emulator_host = None
    else:
        os.environ["FIRESTORE_EMULATOR_HOST"] = emulator_host

    if emulator_host:
        # For emulator we must set project explicitly and use insecure channel
        client_options = ClientOptions(api_endpoint=emulator_host)

    try:
        _firestore_client = firestore.Client(project=project_id, client_options=client_options)
        print(f"[OK] Firestore client initialized (project={project_id})")
    except Exception as exc:
        _firestore_client = None
        print(f"[WARN] Firestore 初始化失败：{exc}")

    return _firestore_client


def get_firestore_client() -> firestore.Client:
    """Get initialized Firestore client or raise error."""
    client = init_firestore()
    if client is None:
        raise RuntimeError("Firestore client 未初始化：请设置 FIRESTORE_PROJECT_ID 或 FIREBASE 项目")
    return client


def close_firestore() -> None:
    """Close Firestore client on shutdown."""
    global _firestore_client
    if _firestore_client is not None:
        _firestore_client.close()
        _firestore_client = None
        print("[OK] Firestore client closed")


__all__ = ["init_firestore", "get_firestore_client", "close_firestore"]

