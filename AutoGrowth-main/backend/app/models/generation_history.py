"""Generation history model."""

from typing import Any

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class GenerationHistory(TimestampMixin, Base):
    __tablename__ = "generation_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    program_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    campaign_name: Mapped[str] = mapped_column(String(512), nullable=False)
    adset_name: Mapped[str] = mapped_column(String(512), nullable=False)
    ad_name: Mapped[str] = mapped_column(String(512), nullable=False)
    onelink_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(back_populates="generation_history")


from .user import User  # circular import guard
