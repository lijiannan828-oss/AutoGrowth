""""Authentication related schemas."""

from pydantic import BaseModel, EmailStr, Field


class AuthenticatedUser(BaseModel):
    """Authenticated user extracted from ID token."""

    email: EmailStr
    email_prefix: str
    name: str | None = None
    picture: str | None = None
    user_id: str | None = Field(default=None, description="Firebase UID")
    is_dev_user: bool = Field(default=False, description="标记是否为开发模式模拟用户")
    auth_token: str | None = Field(
        default=None, description="原始 Authorization Bearer token（可选）"
    )

