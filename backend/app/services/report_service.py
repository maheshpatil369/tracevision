"""Report generation service (spec sections 29-30): assembles real, persisted
analysis data into the shape `pdf_report.generate_forensic_report` expects,
then renders and stores the PDF."""
from __future__ import annotations

import os
from collections import defaultdict
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.cv.video_io import format_timestamp
from app.models.analysis import Analysis
from app.models.detection import ObjectDetection, TrackedObjectRecord
from app.models.evidence import EvidenceFrame
from app.models.face import Face, FacialComparison, ModelRun
from app.models.report import Report
from app.models.timeline import TimelineEvent
from app.models.video import Video
from app.reporting.pdf_report import build_conclusion_text, generate_forensic_report
from app.utils.errors import NotFoundError

settings = get_settings()


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def _object_summary(self, analysis_id: str) -> list[dict]:
        rows = self.db.execute(
            select(ObjectDetection).where(ObjectDetection.analysis_id == analysis_id)
        ).scalars().all()
        by_class: dict[str, list[ObjectDetection]] = defaultdict(list)
        for r in rows:
            by_class[r.class_name].append(r)
        summary = []
        for class_name, items in sorted(by_class.items()):
            timestamps = [i.timestamp_seconds for i in items]
            summary.append({
                "class_name": class_name, "count": len(items),
                "first_seen": format_timestamp(min(timestamps)),
                "last_seen": format_timestamp(max(timestamps)),
            })
        return summary

    def build_report_data(self, analysis_id: str, demo_mode: bool = False) -> dict:
        analysis = self.db.get(Analysis, analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", analysis_id)
        video = self.db.get(Video, analysis.video_id)
        case = video.case

        tracks = self.db.execute(
            select(TrackedObjectRecord).where(TrackedObjectRecord.analysis_id == analysis_id)
            .order_by(TrackedObjectRecord.track_number)
        ).scalars().all()

        faces = self.db.execute(
            select(Face).where(Face.analysis_id == analysis_id).order_by(Face.timestamp_seconds)
        ).scalars().all()

        timeline = self.db.execute(
            select(TimelineEvent).where(TimelineEvent.analysis_id == analysis_id)
            .order_by(TimelineEvent.timestamp_seconds)
        ).scalars().all()

        evidence = self.db.execute(
            select(EvidenceFrame).where(EvidenceFrame.analysis_id == analysis_id)
            .order_by(EvidenceFrame.timestamp_seconds)
        ).scalars().all()

        latest_model = self.db.execute(
            select(ModelRun).order_by(ModelRun.created_at.desc())
        ).scalars().first()

        objects_summary = self._object_summary(analysis_id)

        faces_payload = []
        for f in faces:
            comparison = self.db.execute(
                select(FacialComparison).where(FacialComparison.face_id == f.id)
                .order_by(FacialComparison.created_at.desc())
            ).scalars().first()
            faces_payload.append({
                "face_id": f.id[:8], "timestamp": round(f.timestamp_seconds, 2),
                "landmark_confidence": f.landmark_confidence, "quality_flags": f.quality_flags,
                "classifier_result": (
                    f"{comparison.classifier_prediction} (similarity={comparison.similarity_score})"
                    if comparison and comparison.classifier_prediction else None
                ),
            })

        return {
            "case": {"case_id": case.case_number, "title": case.title,
                     "analyst": case.analyst.full_name if case.analyst else "Not available"},
            "video": {"filename": video.original_filename,
                      "duration_display": format_timestamp(video.duration_seconds),
                      "width": video.width, "height": video.height, "fps": round(video.fps, 2),
                      "total_frames": video.total_frames, "file_format": video.file_format},
            "analysis": {"created_at": analysis.created_at.isoformat(),
                         "settings_summary": analysis.settings_summary()},
            "objects_summary": objects_summary,
            "tracked_objects": [t.to_dict() for t in tracks],
            "faces": faces_payload,
            "timeline": [
                {"timestamp": format_timestamp(e.timestamp_seconds), "description": e.description,
                 "confidence": e.confidence} for e in timeline
            ],
            "evidence_frames": [
                {"evidence_id": e.id[:8], "timestamp": round(e.timestamp_seconds, 2),
                 "reason": e.reason, "image_path": e.annotated_frame_path or e.original_frame_path}
                for e in evidence
            ],
            "model_info": {
                "detector": analysis.detector_backend or "Not available",
                "tracker": analysis.tracker_name or "Not available",
                "facial_model": "MediaPipe FaceLandmarker (468-point)" if faces else "Not available",
                "classifier": latest_model.model_version if latest_model else "Not available",
                "metrics": {
                    "accuracy": latest_model.accuracy, "precision": latest_model.precision,
                    "recall": latest_model.recall, "f1_score": latest_model.f1_score,
                } if latest_model else {},
            },
            "demo_mode": demo_mode,
            "conclusion": build_conclusion_text(objects_summary, [t.to_dict() for t in tracks], faces_payload),
        }

    def generate(self, analysis_id: str, demo_mode: bool = False) -> Report:
        analysis = self.db.get(Analysis, analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", analysis_id)
        video = self.db.get(Video, analysis.video_id)
        case = video.case

        existing_count = self.db.execute(
            select(Report).where(Report.analysis_id == analysis_id)
        ).scalars().all()
        version = len(existing_count) + 1

        report = Report(case_id=case.id, analysis_id=analysis_id, status="generating", version=version)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        try:
            data = self.build_report_data(analysis_id, demo_mode=demo_mode)
            os.makedirs(settings.REPORTS_DIRECTORY, exist_ok=True)
            filename = f"TRACEVISION_{case.case_number}_ANALYSIS-{analysis_id[:8]}_v{version}.pdf"
            file_path = os.path.join(settings.REPORTS_DIRECTORY, filename)
            generate_forensic_report(file_path, data)

            report.status = "completed"
            report.file_path = file_path
            report.filename = filename
        except Exception as exc:  # noqa: BLE001
            report.status = "failed"
            report.error_message = str(exc)
            self.db.commit()
            raise
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_report(self, report_id: str) -> Report:
        report = self.db.get(Report, report_id)
        if not report:
            raise NotFoundError("Report", report_id)
        return report

    def list_reports_for_case(self, case_id: str) -> list[Report]:
        rows = self.db.execute(
            select(Report).where(Report.case_id == case_id).order_by(Report.created_at.desc())
        ).scalars().all()
        return list(rows)
