"""Security helpers for token verification and auth."""

from __future__ import annotations

from typing import Any, Dict

from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings


class AuthenticationError(Exception):
    """Raised when ID token verification fails."""


_request_adapter = requests.Request()


def verify_firebase_token(token: str) -> Dict[str, Any]:
    """Verify Firebase ID token and return decoded payload."""
    if not token:
        raise AuthenticationError("Missing ID token")

    if not settings.firebase_project_id:
        raise AuthenticationError("Firebase project ID is not configured")

    try:
        payload = id_token.verify_firebase_token(
            token,
            _request_adapter,
            audience=settings.firebase_project_id,
        )
    except ValueError as exc:
        raise AuthenticationError("Invalid or expired ID token") from exc

    return payload


