"""Dashboard aggregate statistics (spec section 6) — every number here is a
real SQL COUNT against stored data; nothing is a placeholder."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.case import Case
from app.models.detection import ObjectDetection, TrackedObjectRecord
from app.models.face import Face
from app.models.analysis import Analysis
from app.models.evidence import EvidenceFrame
from app.models.report import Report
from app.models.video import Video

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(db: Session = Depends(get_db)):
    def count(model) -> int:
        return db.execute(select(func.count()).select_from(model)).scalar_one()

    recent_cases = db.execute(select(Case).order_by(Case.created_at.desc()).limit(5)).scalars().all()
    recent_analyses = db.execute(select(Analysis).order_by(Analysis.created_at.desc()).limit(5)).scalars().all()

    data = {
        "total_cases": count(Case),
        "total_videos_processed": count(Video),
        "total_analyses": count(Analysis),
        "total_detected_objects": count(ObjectDetection),
        "total_tracked_objects": count(TrackedObjectRecord),
        "total_detected_faces": count(Face),
        "total_evidence_frames": count(EvidenceFrame),
        "total_reports_generated": db.execute(
            select(func.count()).select_from(Report).where(Report.status == "completed")
        ).scalar_one(),
        "recent_cases": [c.to_dict() for c in recent_cases],
        "recent_analyses": [a.to_dict() for a in recent_analyses],
    }
    return {"success": True, "data": data}
