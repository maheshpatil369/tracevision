from __future__ import annotations

import datetime
from typing import List, Optional

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin

CASE_STATUSES = ("open", "in_progress", "closed", "archived")


class Case(Base, UUIDPKMixin, TimestampMixin):
    """A forensic case (spec section 7). `case_number` is the human-readable,
    unique identifier shown throughout the UI/reports (e.g. CASE-2026-001);
    `id` is the internal UUID primary key."""
    __tablename__ = "cases"
    __table_args__ = (Index("ix_cases_case_number", "case_number", unique=True),)

    case_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    analyst_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    analyst: Mapped[Optional["User"]] = relationship(back_populates="cases")

    videos: Mapped[List["Video"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship(back_populates="case", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "case_number": self.case_number, "title": self.title,
            "description": self.description, "status": self.status, "notes": self.notes,
            "analyst_id": self.analyst_id,
            "analyst_name": self.analyst.full_name if self.analyst else None,
            "video_count": len(self.videos) if self.videos is not None else 0,
            "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat(),
        }
