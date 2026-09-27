from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin

EVIDENCE_TRIGGERS = (
    "first_appearance", "last_appearance", "high_confidence_detection",
    "face_detected", "important_event", "analyst_selected",
)


class EvidenceFrame(Base, UUIDPKMixin, TimestampMixin):
    """A saved evidence frame (spec section 15). Not every processed frame is
    stored — only ones matching an EVIDENCE_TRIGGERS reason — to avoid
    unbounded storage growth."""
    __tablename__ = "evidence_frames"

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), nullable=False)
    analysis: Mapped["Analysis"] = relationship(back_populates="evidence_frames")

    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    object_ids: Mapped[list] = mapped_column(JSON, default=list)      # tracked_object ids involved
    object_types: Mapped[list] = mapped_column(JSON, default=list)
    confidence_values: Mapped[list] = mapped_column(JSON, default=list)

    original_frame_path: Mapped[str] = mapped_column(String(500), nullable=False)
    annotated_frame_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "analysis_id": self.analysis_id, "frame_number": self.frame_number,
            "timestamp": round(self.timestamp_seconds, 3), "reason": self.reason,
            "object_ids": self.object_ids, "object_types": self.object_types,
            "confidence_values": self.confidence_values,
            "original_frame_path": self.original_frame_path,
            "annotated_frame_path": self.annotated_frame_path,
            "created_at": self.created_at.isoformat(),
        }
