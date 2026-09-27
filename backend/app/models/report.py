from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin

REPORT_STATUSES = ("pending", "generating", "completed", "failed")


class Report(Base, UUIDPKMixin, TimestampMixin):
    """A generated forensic PDF report (spec sections 29-30)."""
    __tablename__ = "reports"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), nullable=False)
    case: Mapped["Case"] = relationship(back_populates="reports")

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), nullable=False)
    analysis: Mapped["Analysis"] = relationship(back_populates="reports")

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "case_id": self.case_id, "analysis_id": self.analysis_id,
            "status": self.status, "version": self.version, "filename": self.filename,
            "error_message": self.error_message, "created_at": self.created_at.isoformat(),
        }
