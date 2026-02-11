"""Common API dependencies."""

from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.security import AuthenticationError, verify_firebase_token
from app.schemas.auth import AuthenticatedUser

DEV_AUTH_TOKEN = "dev-token-123"
DEV_USER = AuthenticatedUser(
    email="Beckett@spoonlabs-partners.com",
    email_prefix="Beckett",
    name="Beckett",
    picture=None,
    user_id="dev-user",
    is_dev_user=True,
    auth_token=DEV_AUTH_TOKEN,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide an async database session for request scope."""
    async with get_session() as session:
        yield session


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    """Validate Authorization header and return authenticated user."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = authorization.split(" ", 1)[1].strip()

    if settings.app_env == "development" and token == DEV_AUTH_TOKEN:
        return DEV_USER

    try:
        payload = verify_firebase_token(token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email claim missing in ID token",
        )

    domain = email.split("@")[-1]
    allowed_domains = settings.allowed_email_domains
    if allowed_domains and domain not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="邮箱域名未获授权",
        )

    email_prefix = email.split("@")[0]

    return AuthenticatedUser(
        email=email,
        email_prefix=email_prefix,
        name=payload.get("name"),
        picture=payload.get("picture"),
        user_id=payload.get("user_id") or payload.get("uid"),
        auth_token=token,
    )


def get_current_user_optional(authorization: str | None = Header(default=None)) -> AuthenticatedUser | None:
    """可选的用户认证，未登录时返回 None"""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()

    if settings.app_env == "development" and token == DEV_AUTH_TOKEN:
        return DEV_USER

    try:
        payload = verify_firebase_token(token)
    except AuthenticationError:
        return None

    email = payload.get("email")
    if not email:
        return None

    email_prefix = email.split("@")[0]

    return AuthenticatedUser(
        email=email,
        email_prefix=email_prefix,
        name=payload.get("name"),
        picture=payload.get("picture"),
        user_id=payload.get("user_id") or payload.get("uid"),
        auth_token=token,
    )
