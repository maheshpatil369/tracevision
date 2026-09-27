from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin


class ObjectDetection(Base, UUIDPKMixin, TimestampMixin):
    """A single per-frame detection result (spec section 12). Many rows per
    tracked object; kept separate from TrackedObjectRecord so raw detector
    output and the tracker's aggregated identity are both auditable."""
    __tablename__ = "object_detections"
    __table_args__ = (Index("ix_detections_analysis_frame", "analysis_id", "frame_number"),)

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), nullable=False)
    analysis: Mapped["Analysis"] = relationship(back_populates="detections")

    track_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tracked_objects.id"), nullable=True)
    track: Mapped[Optional["TrackedObjectRecord"]] = relationship(back_populates="detections")

    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    class_id: Mapped[int] = mapped_column(Integer, nullable=False)
    class_name: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)
    detector_backend: Mapped[str] = mapped_column(String(30), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "analysis_id": self.analysis_id, "track_id": self.track_id,
            "frame_number": self.frame_number, "timestamp": round(self.timestamp_seconds, 3),
            "class_id": self.class_id, "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": {"x": self.bbox_x, "y": self.bbox_y, "width": self.bbox_width, "height": self.bbox_height},
            "detector_backend": self.detector_backend,
        }


class TrackedObjectRecord(Base, UUIDPKMixin, TimestampMixin):
    """One tracked identity across the whole video (spec section 13-14)."""
    __tablename__ = "tracked_objects"

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), nullable=False)
    analysis: Mapped["Analysis"] = relationship(back_populates="tracked_objects")

    track_number: Mapped[int] = mapped_column(Integer, nullable=False)  # per-analysis display ID, e.g. "Person #1"
    class_name: Mapped[str] = mapped_column(String(50), nullable=False)
    first_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    last_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    first_timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    last_timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    detection_count: Mapped[int] = mapped_column(Integer, nullable=False)
    average_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    min_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    max_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    trajectory: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    detections: Mapped[list["ObjectDetection"]] = relationship(back_populates="track")
    faces: Mapped[list["Face"]] = relationship(back_populates="track")

    @property
    def duration_seconds(self) -> float:
        return round(self.last_timestamp - self.first_timestamp, 3)

    @property
    def display_label(self) -> str:
        return f"{self.class_name.capitalize()} #{self.track_number}"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "analysis_id": self.analysis_id, "track_number": self.track_number,
            "display_label": self.display_label, "class_name": self.class_name,
            "first_frame": self.first_frame, "last_frame": self.last_frame,
            "first_timestamp": round(self.first_timestamp, 3), "last_timestamp": round(self.last_timestamp, 3),
            "duration_seconds": self.duration_seconds, "detection_count": self.detection_count,
            "average_confidence": round(self.average_confidence, 4),
            "min_confidence": round(self.min_confidence, 4), "max_confidence": round(self.max_confidence, 4),
            "trajectory": self.trajectory,
        }
