from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.analysis import Analysis, ProcessingJob
from app.models.detection import ObjectDetection, TrackedObjectRecord
from app.models.evidence import EvidenceFrame
from app.models.face import Face
from app.models.timeline import TimelineEvent
from app.models.video import Video
from app.utils.errors import NotFoundError, ValidationAppError

settings = get_settings()


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def create_analysis(self, video_id: str, detection_confidence: float = None,
                         iou_threshold: float = None, frame_interval: int = None,
                         tracker: str = "auto") -> Analysis:
        video = self.db.get(Video, video_id)
        if not video:
            raise NotFoundError("Video", video_id)
        if tracker not in ("auto", "iou", "bytetrack"):
            raise ValidationAppError("INVALID_TRACKER", "tracker must be one of auto, iou, bytetrack.")

        analysis = Analysis(
            video_id=video_id, status="queued",
            detection_confidence=detection_confidence if detection_confidence is not None else settings.DETECTION_CONFIDENCE,
            iou_threshold=iou_threshold if iou_threshold is not None else settings.DETECTION_IOU_THRESHOLD,
            frame_interval=frame_interval if frame_interval is not None else settings.FRAME_INTERVAL,
            tracker_name=tracker,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_analysis(self, analysis_id: str) -> Analysis:
        analysis = self.db.get(Analysis, analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", analysis_id)
        return analysis

    def list_analyses_for_video(self, video_id: str) -> list[Analysis]:
        rows = self.db.execute(
            select(Analysis).where(Analysis.video_id == video_id).order_by(Analysis.created_at.desc())
        ).scalars().all()
        return list(rows)

    def latest_job(self, analysis_id: str) -> Optional[ProcessingJob]:
        return self.db.execute(
            select(ProcessingJob).where(ProcessingJob.analysis_id == analysis_id)
            .order_by(ProcessingJob.created_at.desc())
        ).scalars().first()

    def cancel_analysis(self, analysis_id: str) -> Analysis:
        analysis = self.get_analysis(analysis_id)
        if analysis.status not in ("queued", "processing"):
            raise ValidationAppError("CANNOT_CANCEL", f"Analysis is '{analysis.status}' and cannot be cancelled.")
        analysis.status = "cancelled"
        job = self.latest_job(analysis_id)
        if job and job.status in ("queued", "processing"):
            job.status = "cancelled"
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_objects_summary(self, analysis_id: str) -> list[dict]:
        from collections import defaultdict
        from app.cv.video_io import format_timestamp
        rows = self.db.execute(
            select(ObjectDetection).where(ObjectDetection.analysis_id == analysis_id)
        ).scalars().all()
        by_class = defaultdict(list)
        for r in rows:
            by_class[r.class_name].append(r)
        out = []
        for class_name, items in sorted(by_class.items()):
            ts = [i.timestamp_seconds for i in items]
            out.append({"class_name": class_name, "count": len(items),
                        "first_seen": format_timestamp(min(ts)), "last_seen": format_timestamp(max(ts))})
        return out

    def get_tracked_objects(self, analysis_id: str) -> list[dict]:
        rows = self.db.execute(
            select(TrackedObjectRecord).where(TrackedObjectRecord.analysis_id == analysis_id)
            .order_by(TrackedObjectRecord.track_number)
        ).scalars().all()
        return [r.to_dict() for r in rows]

    def get_faces(self, analysis_id: str, include_landmarks: bool = False) -> list[dict]:
        rows = self.db.execute(
            select(Face).where(Face.analysis_id == analysis_id).order_by(Face.timestamp_seconds)
        ).scalars().all()
        return [r.to_dict(include_landmarks=include_landmarks) for r in rows]

    def get_evidence(self, analysis_id: str) -> list[dict]:
        rows = self.db.execute(
            select(EvidenceFrame).where(EvidenceFrame.analysis_id == analysis_id)
            .order_by(EvidenceFrame.timestamp_seconds)
        ).scalars().all()
        return [r.to_dict() for r in rows]

    def get_timeline(self, analysis_id: str) -> list[dict]:
        rows = self.db.execute(
            select(TimelineEvent).where(TimelineEvent.analysis_id == analysis_id)
            .order_by(TimelineEvent.timestamp_seconds)
        ).scalars().all()
        return [r.to_dict() for r in rows]
