from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class VideoOut(BaseModel):
    id: str
    case_id: str
    original_filename: str
    file_format: str
    file_size_bytes: int
    sha256: str
    width: int
    height: int
    fps: float
    total_frames: int
    duration_seconds: float
    uploaded_at: str


class AnalysisSettings(BaseModel):
    detection_confidence: float = 0.4
    iou_threshold: float = 0.5
    frame_interval: int = 5
    tracker: str = "auto"  # "auto" | "iou" | "bytetrack"


class AnalysisOut(BaseModel):
    id: str
    video_id: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    detection_confidence: float
    iou_threshold: float
    frame_interval: int
    tracker_name: str
    detector_backend: Optional[str]
    error_message: Optional[str]
    settings_summary: str
    created_at: str


class ProcessingJobOut(BaseModel):
    id: str
    analysis_id: str
    status: str
    current_stage: Optional[str]
    progress_percent: int
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]
