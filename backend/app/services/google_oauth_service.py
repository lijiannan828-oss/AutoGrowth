"""Google OAuth code exchange and secure refresh token storage."""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from typing import List, Optional

import requests
from cryptography.fernet import Fernet, InvalidToken
from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.config import settings
from app.core.firestore import get_firestore_client
from app.schemas.auth import AuthenticatedUser

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class OAuthConfigurationError(RuntimeError):
    """Raised when OAuth configuration is missing."""


class TokenStorageError(RuntimeError):
    """Raised when refresh token storage fails."""


def _get_fernet() -> Fernet:
    key = settings.oauth_token_encryption_key
    if not key:
        raise OAuthConfigurationError("未配置 OAUTH_TOKEN_ENCRYPTION_KEY，无法加密刷新令牌")
    try:
        # Allow raw 32-byte key (base64 or plain)
        if len(key) == 44 and key.endswith("="):
            fernet_key = key.encode("utf-8")
        else:
            fernet_key = base64.urlsafe_b64encode(key.encode("utf-8"))
        return Fernet(fernet_key)
    except Exception as exc:
        raise OAuthConfigurationError("OAUTH_TOKEN_ENCRYPTION_KEY 无法用于 Fernet") from exc


@dataclass
class OAuthTokenResult:
    access_token: Optional[str]
    expires_in: Optional[int]
    refresh_token: str
    scope: List[str]
    token_type: Optional[str]


def exchange_code(auth_code: str, redirect_uri: Optional[str] = None, scope: Optional[List[str]] = None) -> OAuthTokenResult:
    """Exchange authorization code for access + refresh token."""
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise OAuthConfigurationError("未配置 GOOGLE_OAUTH_CLIENT_ID / SECRET")

    payload = {
        "code": auth_code,
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "redirect_uri": redirect_uri or settings.google_oauth_redirect_uri,
        "grant_type": "authorization_code",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(TOKEN_ENDPOINT, data=payload, headers=headers, timeout=20)
    if response.status_code != 200:
        raise RuntimeError(f"交换授权码失败：{response.text}")

    data = response.json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Google 返回结果缺少 refresh_token，请确认授权范围包含 offline access")

    scopes = scope or data.get("scope", "").split()
    if not scopes:
        scopes = DEFAULT_SCOPES

    return OAuthTokenResult(
        access_token=data.get("access_token"),
        expires_in=data.get("expires_in"),
        refresh_token=refresh_token,
        scope=scopes,
        token_type=data.get("token_type"),
    )


def _token_collection(client: firestore.Client) -> firestore.CollectionReference:
    namespace = settings.firestore_namespace or "default"
    collection_name = f"{namespace}_oauth_tokens"
    return client.collection(collection_name)


def store_refresh_token(user: AuthenticatedUser, token_result: OAuthTokenResult) -> str:
    """Encrypt and store refresh token, returning a token reference id."""
    client = get_firestore_client()
    doc_id = f"token_{uuid.uuid4().hex}"
    encrypted = _get_fernet().encrypt(token_result.refresh_token.encode("utf-8")).decode("utf-8")
    doc = {
        "userId": user.user_id,
        "userEmail": user.email,
        "provider": "google",
        "scopes": token_result.scope,
        "refreshToken": encrypted,
        "createdAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
        "tokenType": token_result.token_type,
    }
    _token_collection(client).document(doc_id).set(doc)
    return doc_id


def retrieve_refresh_token(token_id: str) -> str:
    """Retrieve and decrypt refresh token for later job usage."""
    client = get_firestore_client()
    doc = _token_collection(client).document(token_id).get()
    if not doc.exists:
        raise TokenStorageError("指定的 token 不存在")
    data = doc.to_dict()
    encrypted = data.get("refreshToken")
    if not encrypted:
        raise TokenStorageError("Token 数据缺少 refreshToken 字段")
    try:
        decrypted = _get_fernet().decrypt(encrypted.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken as exc:
        raise TokenStorageError("刷新令牌解密失败") from exc


def lookup_latest_token_ref(user: AuthenticatedUser) -> Optional[str]:
    """Return latest refresh token doc id for given user, if exists."""
    client = get_firestore_client()
    collection = _token_collection(client)

    query = None
    if user.user_id:
        query = collection.where("userId", "==", user.user_id)
    else:
        query = collection.where("userEmail", "==", user.email)

    query = query.order_by("updatedAt", direction=firestore.Query.DESCENDING).limit(1)
    docs = list(query.stream())
    if not docs:
        return None
    return docs[0].id


