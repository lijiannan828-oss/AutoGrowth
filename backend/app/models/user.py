"""User model."""

from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_prefix: Mapped[str] = mapped_column(String(255), nullable=False)

    generation_history: Mapped[list["GenerationHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


from .generation_history import GenerationHistory  # avoid circular import
