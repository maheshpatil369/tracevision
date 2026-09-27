from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api", tags=["objects-tracks-faces-evidence-timeline"])


@router.get("/objects/by-analysis/{analysis_id}")
def get_objects_summary(analysis_id: str, db: Session = Depends(get_db)):
    return {"success": True, "data": AnalysisService(db).get_objects_summary(analysis_id)}


@router.get("/tracks/by-analysis/{analysis_id}")
def get_tracked_objects(analysis_id: str, db: Session = Depends(get_db)):
    return {"success": True, "data": AnalysisService(db).get_tracked_objects(analysis_id)}


@router.get("/faces/by-analysis/{analysis_id}")
def get_faces(analysis_id: str, include_landmarks: bool = False, db: Session = Depends(get_db)):
    return {"success": True, "data": AnalysisService(db).get_faces(analysis_id, include_landmarks=include_landmarks)}


@router.get("/evidence/by-analysis/{analysis_id}")
def get_evidence(analysis_id: str, db: Session = Depends(get_db)):
    return {"success": True, "data": AnalysisService(db).get_evidence(analysis_id)}


@router.get("/timeline/by-analysis/{analysis_id}")
def get_timeline(analysis_id: str, db: Session = Depends(get_db)):
    return {"success": True, "data": AnalysisService(db).get_timeline(analysis_id)}
