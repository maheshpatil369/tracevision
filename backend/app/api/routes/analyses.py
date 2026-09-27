from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.video import AnalysisSettings
from app.services.analysis_service import AnalysisService
from app.utils.errors import AppError
from app.workers.job_runner import submit_analysis_job

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.post("")
def create_and_start_analysis(video_id: str, settings: AnalysisSettings = AnalysisSettings(), db: Session = Depends(get_db)):
    try:
        analysis = AnalysisService(db).create_analysis(
            video_id=video_id, detection_confidence=settings.detection_confidence,
            iou_threshold=settings.iou_threshold, frame_interval=settings.frame_interval,
            tracker=settings.tracker,
        )
        submit_analysis_job(analysis.id)
        return {"success": True, "data": analysis.to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    try:
        return {"success": True, "data": AnalysisService(db).get_analysis(analysis_id).to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.get("/{analysis_id}/status")
def get_analysis_status(analysis_id: str, db: Session = Depends(get_db)):
    try:
        service = AnalysisService(db)
        analysis = service.get_analysis(analysis_id)
        job = service.latest_job(analysis_id)
        return {"success": True, "data": {"analysis": analysis.to_dict(),
                                           "job": job.to_dict() if job else None}}
    except AppError as e:
        raise e.to_http_exception()


@router.get("/by-video/{video_id}")
def list_analyses_for_video(video_id: str, db: Session = Depends(get_db)):
    rows = AnalysisService(db).list_analyses_for_video(video_id)
    return {"success": True, "data": [r.to_dict() for r in rows]}


@router.post("/{analysis_id}/cancel")
def cancel_analysis(analysis_id: str, db: Session = Depends(get_db)):
    try:
        analysis = AnalysisService(db).cancel_analysis(analysis_id)
        return {"success": True, "data": analysis.to_dict()}
    except AppError as e:
        raise e.to_http_exception()
