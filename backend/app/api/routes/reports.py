from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.forensic import ReportGenerateRequest
from app.services.report_service import ReportService
from app.utils.errors import AppError

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("")
def generate_report(payload: ReportGenerateRequest, db: Session = Depends(get_db)):
    try:
        report = ReportService(db).generate(payload.analysis_id, demo_mode=payload.demo_mode)
        return {"success": True, "data": report.to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.get("/by-case/{case_id}")
def list_reports_for_case(case_id: str, db: Session = Depends(get_db)):
    reports = ReportService(db).list_reports_for_case(case_id)
    return {"success": True, "data": [r.to_dict() for r in reports]}


@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    try:
        return {"success": True, "data": ReportService(db).get_report(report_id).to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.get("/{report_id}/download")
def download_report(report_id: str, db: Session = Depends(get_db)):
    try:
        report = ReportService(db).get_report(report_id)
    except AppError as e:
        raise e.to_http_exception()
    if report.status != "completed" or not report.file_path or not os.path.isfile(report.file_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail={
            "code": "REPORT_NOT_READY", "message": "Report is not yet available for download."})
    return FileResponse(report.file_path, media_type="application/pdf", filename=report.filename)
