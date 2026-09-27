from __future__ import annotations

import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin

ANALYSIS_STATUSES = ("queued", "processing", "completed", "failed", "cancelled")

PROCESSING_STAGES = [
    "preparing_video", "reading_metadata", "extracting_frames",
    "detecting_objects", "tracking_objects", "detecting_faces",
    "facial_analysis", "extracting_evidence", "building_timeline",
    "saving_results", "generating_report",
]


class Analysis(Base, UUIDPKMixin, TimestampMixin):
    """One run of the full video-analysis pipeline against a Video
    (spec sections 9-10). Holds the processing settings used, so results are
    reproducible/explainable."""
    __tablename__ = "analyses"

    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False)
    video: Mapped["Video"] = relationship(back_populates="analyses")

    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    # Processing settings (spec section 58) — stored as-run, not just defaults.
    detection_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    iou_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    frame_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    tracker_name: Mapped[str] = mapped_column(String(30), nullable=False)
    detector_backend: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    jobs: Mapped[List["ProcessingJob"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    detections: Mapped[List["ObjectDetection"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    tracked_objects: Mapped[List["TrackedObjectRecord"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    faces: Mapped[List["Face"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    evidence_frames: Mapped[List["EvidenceFrame"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    timeline_events: Mapped[List["TimelineEvent"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")

    def settings_summary(self) -> str:
        return (f"conf={self.detection_confidence}, iou={self.iou_threshold}, "
                f"frame_interval={self.frame_interval}, tracker={self.tracker_name}")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "video_id": self.video_id, "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "detection_confidence": self.detection_confidence, "iou_threshold": self.iou_threshold,
            "frame_interval": self.frame_interval, "tracker_name": self.tracker_name,
            "detector_backend": self.detector_backend, "error_message": self.error_message,
            "settings_summary": self.settings_summary(),
            "created_at": self.created_at.isoformat(),
        }


class ProcessingJob(Base, UUIDPKMixin, TimestampMixin):
    """Background-job bookkeeping for one Analysis run (spec section 10)."""
    __tablename__ = "processing_jobs"

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), nullable=False)
    analysis: Mapped["Analysis"] = relationship(back_populates="jobs")

    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    current_stage: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "analysis_id": self.analysis_id, "status": self.status,
            "current_stage": self.current_stage, "progress_percent": self.progress_percent,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }
