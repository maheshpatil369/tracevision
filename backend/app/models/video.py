from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin


class Video(Base, UUIDPKMixin, TimestampMixin):
    """An uploaded CCTV/video file and its extracted metadata (spec section 8).
    `storage_path` is a generated, sanitized path — never the raw user
    filename — to prevent path traversal; `original_filename` is kept only
    for display/provenance."""
    __tablename__ = "videos"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), nullable=False)
    case: Mapped["Case"] = relationship(back_populates="videos")

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    fps: Mapped[float] = mapped_column(Float, nullable=False)
    total_frames: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    analyses: Mapped[List["Analysis"]] = relationship(back_populates="video", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "case_id": self.case_id, "original_filename": self.original_filename,
            "file_format": self.file_format, "file_size_bytes": self.file_size_bytes,
            "sha256": self.sha256, "width": self.width, "height": self.height,
            "fps": round(self.fps, 3), "total_frames": self.total_frames,
            "duration_seconds": round(self.duration_seconds, 3),
            "uploaded_at": self.created_at.isoformat(),
        }
