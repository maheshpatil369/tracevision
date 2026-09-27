from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin

EVENT_TYPES = (
    "object_entered", "object_exited", "face_detected", "high_confidence_detection",
    "object_interaction", "evidence_captured", "analysis_started", "analysis_completed",
)


class TimelineEvent(Base, UUIDPKMixin, TimestampMixin):
    """One entry in the chronological event timeline (spec section 16)."""
    __tablename__ = "timeline_events"
    __table_args__ = (Index("ix_timeline_analysis_ts", "analysis_id", "timestamp_seconds"),)

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), nullable=False)
    analysis: Mapped["Analysis"] = relationship(back_populates="timeline_events")

    timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    related_track_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tracked_objects.id"), nullable=True)
    related_face_id: Mapped[Optional[str]] = mapped_column(ForeignKey("faces.id"), nullable=True)
    evidence_frame_id: Mapped[Optional[str]] = mapped_column(ForeignKey("evidence_frames.id"), nullable=True)

    def to_dict(self) -> dict:
        from app.cv.video_io import format_timestamp
        return {
            "id": self.id, "analysis_id": self.analysis_id,
            "timestamp": format_timestamp(self.timestamp_seconds),
            "timestamp_seconds": round(self.timestamp_seconds, 3),
            "event_type": self.event_type, "description": self.description,
            "confidence": round(self.confidence, 4) if self.confidence is not None else None,
            "related_track_id": self.related_track_id, "related_face_id": self.related_face_id,
            "evidence_frame_id": self.evidence_frame_id,
        }
