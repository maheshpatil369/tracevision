"""
The analysis orchestrator (spec sections 9-10): runs the full pipeline
UPLOAD -> METADATA -> FRAMES -> DETECTION -> TRACKING -> FACES -> LANDMARKS
-> 3D -> GEOMETRY -> ML -> EVIDENCE -> TIMELINE -> STORE -> [REPORT] against
one Analysis row, updating a ProcessingJob's stage/progress as it goes so the
frontend can show real, non-fake progress (spec section 10).

This module has NO FastAPI imports — it is invoked from a background thread
by app/workers/job_runner.py, and can equally be invoked directly from a
script or test.
"""
from __future__ import annotations

import datetime
import os
import traceback
from typing import Callable, Dict, List, Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.cv.detector import Detection, build_default_detector
from app.cv.face_mesh import FaceLandmarker, ModelAssetMissingError, build_3d_representation
from app.cv.geometry import FaceGeometryEngine
from app.cv.tracker import IouTracker, Tracker, build_default_tracker
from app.cv.video_io import format_timestamp, iter_frames
from app.models.analysis import PROCESSING_STAGES, Analysis, ProcessingJob
from app.models.detection import ObjectDetection, TrackedObjectRecord
from app.models.evidence import EvidenceFrame
from app.models.face import Face
from app.models.timeline import TimelineEvent
from app.models.video import Video

settings = get_settings()

FACE_ELIGIBLE_CLASSES = {"person"}
HIGH_CONFIDENCE_THRESHOLD = 0.9


class AnalysisOrchestrator:
    def __init__(self, db: Session, on_progress: Optional[Callable[[str, int], None]] = None):
        self.db = db
        self._on_progress = on_progress or (lambda stage, pct: None)
        self.geometry_engine = FaceGeometryEngine()

    def _progress(self, stage: str, pct: int):
        self._on_progress(stage, pct)

    def run(self, analysis_id: str) -> Analysis:
        analysis = self.db.get(Analysis, analysis_id)
        if analysis is None:
            raise ValueError(f"Analysis '{analysis_id}' not found.")
        video = self.db.get(Video, analysis.video_id)

        job = ProcessingJob(analysis_id=analysis.id, status="processing",
                             started_at=datetime.datetime.utcnow(), current_stage="preparing_video")
        self.db.add(job)
        analysis.status = "processing"
        analysis.started_at = datetime.datetime.utcnow()
        self.db.commit()

        try:
            self._run_pipeline(analysis, video, job)
            analysis.status = "completed"
            analysis.completed_at = datetime.datetime.utcnow()
            job.status = "completed"
            job.progress_percent = 100
            job.completed_at = datetime.datetime.utcnow()
            job.current_stage = "generating_report"
            self.db.commit()
        except Exception as exc:  # noqa: BLE001 - must persist failure state, not crash the worker thread
            analysis.status = "failed"
            analysis.error_message = str(exc)
            job.status = "failed"
            job.error_message = f"{exc}\n{traceback.format_exc()[-2000:]}"
            job.completed_at = datetime.datetime.utcnow()
            self.db.commit()
            raise
        return analysis

    # ------------------------------------------------------------------ core --
    def _run_pipeline(self, analysis: Analysis, video: Video, job: ProcessingJob):
        n_stages = len(PROCESSING_STAGES)

        def stage_progress(stage_name: str):
            idx = PROCESSING_STAGES.index(stage_name)
            pct = int(round((idx / n_stages) * 100))
            job.current_stage = stage_name
            job.progress_percent = pct
            self.db.commit()
            self._progress(stage_name, pct)

        stage_progress("preparing_video")
        weights_path = os.path.join(settings.MODEL_DIRECTORY, settings.YOLO_MODEL)
        detector = build_default_detector(weights_path if os.path.isfile(weights_path) else None)
        analysis.detector_backend = detector.backend_name

        tracker_name = analysis.tracker_name
        tracker: Tracker
        if tracker_name == "iou":
            tracker = IouTracker(iou_threshold=settings.TRACKER_IOU_THRESHOLD, max_age=settings.TRACKER_MAX_AGE)
        else:
            tracker = build_default_tracker(prefer_bytetrack=(tracker_name != "iou"), frame_rate=int(video.fps or 25))
        analysis.tracker_name = "bytetrack" if type(tracker).__name__ == "ByteTrackAdapter" else "iou"
        self.db.commit()

        face_model_path = os.path.join(settings.MODEL_DIRECTORY, settings.FACE_MODEL_FILENAME)
        face_landmarker: Optional[FaceLandmarker] = None
        if os.path.isfile(face_model_path):
            try:
                face_landmarker = FaceLandmarker(
                    model_dir=settings.MODEL_DIRECTORY, model_filename=settings.FACE_MODEL_FILENAME,
                    min_detection_confidence=settings.FACE_MIN_DETECTION_CONFIDENCE, running_mode="VIDEO")
            except ModelAssetMissingError:
                face_landmarker = None
        # If face_landmarker is None, facial analysis is skipped for this run
        # and is reported as unavailable rather than faked (spec section 68).

        stage_progress("reading_metadata")
        os.makedirs(settings.EVIDENCE_DIRECTORY, exist_ok=True)

        stage_progress("extracting_frames")
        detection_rows: List[ObjectDetection] = []
        face_rows: List[Face] = []
        track_id_to_number: Dict[int, int] = {}
        track_first_evidence_saved: set = set()
        face_count = 0
        timeline_events: List[TimelineEvent] = []

        try:
            for frame_number, timestamp, frame in iter_frames(
                    video.storage_path, frame_interval=analysis.frame_interval,
                    max_dimension=settings.MAX_PROCESSING_DIMENSION):

                stage_progress("detecting_objects")
                dets = detector.detect(
                    frame, frame_number, timestamp,
                    confidence_threshold=analysis.detection_confidence,
                    iou_threshold=analysis.iou_threshold,
                )

                stage_progress("tracking_objects")
                tracker.update(dets)

                for det in dets:
                    tid = tracker.get_track_id_for(det)
                    if tid is not None and tid not in track_id_to_number:
                        track_id_to_number[tid] = len(track_id_to_number) + 1

                    row = ObjectDetection(
                        analysis_id=analysis.id, frame_number=det.frame_number,
                        timestamp_seconds=det.timestamp, class_id=det.class_id,
                        class_name=det.class_name, confidence=det.confidence,
                        bbox_x=det.x, bbox_y=det.y, bbox_width=det.width, bbox_height=det.height,
                        detector_backend=det.detector_backend,
                    )
                    row._internal_track_num = tid  # temp attr, resolved to DB id after tracker finalizes
                    detection_rows.append(row)

                    if det.confidence >= HIGH_CONFIDENCE_THRESHOLD:
                        timeline_events.append(TimelineEvent(
                            analysis_id=analysis.id, timestamp_seconds=det.timestamp,
                            event_type="high_confidence_detection",
                            description=f"{det.class_name.capitalize()} detected with high confidence",
                            confidence=det.confidence,
                        ))

                    if face_landmarker is not None and det.class_name in FACE_ELIGIBLE_CLASSES:
                        stage_progress("detecting_faces")
                        crop = _safe_crop(frame, det)
                        if crop is not None and crop.size > 0:
                            result = face_landmarker.process(crop, timestamp_ms=int(timestamp * 1000))
                            if result.face_found:
                                stage_progress("facial_analysis")
                                face_count += 1
                                rep3d = build_3d_representation(result.landmarks)
                                geom = self.geometry_engine.build_feature_vector(result.landmarks)
                                face_row = Face(
                                    analysis_id=analysis.id, frame_number=det.frame_number,
                                    timestamp_seconds=det.timestamp, face_found=True,
                                    num_faces_in_frame=result.num_faces,
                                    landmark_confidence=result.landmark_confidence,
                                    quality_flags=result.quality_flags, bbox=result.bbox,
                                    landmarks=result.landmarks.tolist(),
                                    landmark_model_version="mediapipe-face_landmarker",
                                    representation_3d=rep3d,
                                    geometric_features=geom.to_dict(),
                                    feature_set_version=geom.version,
                                )
                                face_row._internal_track_num = tid
                                self.db.add(face_row)
                                self.db.flush()
                                face_rows.append(face_row)
                                timeline_events.append(TimelineEvent(
                                    analysis_id=analysis.id, timestamp_seconds=det.timestamp,
                                    event_type="face_detected",
                                    description="Face detected" + (
                                        f" ({', '.join(result.quality_flags)})" if result.quality_flags else ""),
                                    confidence=result.landmark_confidence,
                                    related_face_id=face_row.id,
                                ))

                    # Evidence: first appearance of each track.
                    if tid is not None and tid not in track_first_evidence_saved:
                        track_first_evidence_saved.add(tid)
                        stage_progress("extracting_evidence")
                        ev = self._save_evidence_frame(analysis.id, frame, det, "first_appearance")
                        self.db.add(ev)
                        self.db.flush()
                        timeline_events.append(TimelineEvent(
                            analysis_id=analysis.id, timestamp_seconds=det.timestamp,
                            event_type="object_entered",
                            description=f"{det.class_name.capitalize()} #{track_id_to_number.get(tid, tid)} entered",
                            confidence=det.confidence, evidence_frame_id=ev.id,
                        ))
        finally:
            if face_landmarker is not None:
                face_landmarker.close()

        stage_progress("tracking_objects")
        finalized_tracks = tracker.finalize()
        track_number_map: Dict[int, int] = {}
        track_db_id_map: Dict[int, str] = {}
        for i, t in enumerate(finalized_tracks, start=1):
            track_number_map[t.track_id] = i
            record = TrackedObjectRecord(
                analysis_id=analysis.id, track_number=i, class_name=t.class_name,
                first_frame=t.first_frame, last_frame=t.last_frame,
                first_timestamp=t.first_timestamp, last_timestamp=t.last_timestamp,
                detection_count=t.detection_count, average_confidence=t.average_confidence,
                min_confidence=t.min_confidence, max_confidence=t.max_confidence,
                trajectory=t.trajectory,
            )
            self.db.add(record)
            self.db.flush()
            track_db_id_map[t.track_id] = record.id
            timeline_events.append(TimelineEvent(
                analysis_id=analysis.id, timestamp_seconds=t.last_timestamp,
                event_type="object_exited",
                description=f"{t.class_name.capitalize()} #{i} exited",
                confidence=t.average_confidence,
            ))

        for row in detection_rows:
            tid = getattr(row, "_internal_track_num", None)
            if tid is not None and tid in track_db_id_map:
                row.track_id = track_db_id_map[tid]
            self.db.add(row)

        for f in face_rows:
            tid = getattr(f, "_internal_track_num", None)
            if tid is not None and tid in track_db_id_map:
                f.track_id = track_db_id_map[tid]

        stage_progress("building_timeline")
        for ev in timeline_events:
            self.db.add(ev)

        stage_progress("saving_results")
        self.db.commit()


    def _save_evidence_frame(self, analysis_id: str, frame: np.ndarray, det: Detection, reason: str) -> EvidenceFrame:
        evidence_dir = os.path.join(settings.EVIDENCE_DIRECTORY, analysis_id)
        os.makedirs(evidence_dir, exist_ok=True)
        base_name = f"frame{det.frame_number}_{reason}"
        original_path = os.path.join(evidence_dir, f"{base_name}_original.jpg")
        annotated_path = os.path.join(evidence_dir, f"{base_name}_annotated.jpg")

        cv2.imwrite(original_path, frame)

        annotated = frame.copy()
        x0, y0 = int(det.x), int(det.y)
        x1, y1 = int(det.x + det.width), int(det.y + det.height)
        cv2.rectangle(annotated, (x0, y0), (x1, y1), (0, 200, 255), 2)
        label = f"{det.class_name} {det.confidence:.2f}"
        cv2.putText(annotated, label, (x0, max(0, y0 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
        cv2.imwrite(annotated_path, annotated)

        return EvidenceFrame(
            analysis_id=analysis_id, frame_number=det.frame_number, timestamp_seconds=det.timestamp,
            reason=reason, object_ids=[], object_types=[det.class_name], confidence_values=[det.confidence],
            original_frame_path=original_path, annotated_frame_path=annotated_path,
        )


def _safe_crop(frame: np.ndarray, det: Detection) -> Optional[np.ndarray]:
    h, w = frame.shape[:2]
    x0, y0 = max(0, int(det.x)), max(0, int(det.y))
    x1, y1 = min(w, int(det.x + det.width)), min(h, int(det.y + det.height))
    if x1 <= x0 or y1 <= y0:
        return None
    return frame[y0:y1, x0:x1]
