"""Program Info model for storing program information from Google Sheets."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ProgramInfo(TimestampMixin, Base):
    """Program information stored in database, synced from Google Sheets."""
    
    __tablename__ = "program_info"
    
    program_code: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    program_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    sub_title: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    synopsis: Mapped[str] = mapped_column(Text, default="", nullable=False)
    episode_count: Mapped[int] = mapped_column(Integer, nullable=False)
    release_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    content_information: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    program_shortner: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    title_en_shortener: Mapped[str] = mapped_column(String(500), nullable=False)
    season_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    __table_args__ = (
        Index("idx_program_info_program_id", "program_id"),
        Index("idx_program_info_release_date", "release_date"),
        Index("idx_program_info_updated_at", "updated_at"),
    )

