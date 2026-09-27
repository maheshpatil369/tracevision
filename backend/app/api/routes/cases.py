from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.case import CaseCreate, CaseUpdate
from app.services.case_service import CaseService
from app.utils.errors import AppError

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("")
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    try:
        case = CaseService(db).create_case(**payload.model_dump())
        return {"success": True, "data": case.to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.get("")
def list_cases(page: int = 1, page_size: int = 20, status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    cases, total = CaseService(db).list_cases(page=page, page_size=page_size, status=status)
    return {"success": True, "data": {"items": [c.to_dict() for c in cases],
                                       "page": page, "page_size": page_size, "total": total}}


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    try:
        return {"success": True, "data": CaseService(db).get_case(case_id).to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.patch("/{case_id}")
def update_case(case_id: str, payload: CaseUpdate, db: Session = Depends(get_db)):
    try:
        case = CaseService(db).update_case(case_id, **payload.model_dump(exclude_unset=True))
        return {"success": True, "data": case.to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.post("/{case_id}/archive")
def archive_case(case_id: str, db: Session = Depends(get_db)):
    try:
        case = CaseService(db).archive_case(case_id)
        return {"success": True, "data": case.to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.delete("/{case_id}")
def delete_case(case_id: str, db: Session = Depends(get_db)):
    try:
        CaseService(db).delete_case(case_id)
        return {"success": True, "data": {"message": "Case deleted."}}
    except AppError as e:
        raise e.to_http_exception()
