from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.video import Video
from app.utils.errors import NotFoundError
from app.utils.validation import validate_case_number, validate_case_status, validate_pagination


class CaseService:
    def __init__(self, db: Session):
        self.db = db

    def create_case(self, case_number: str, title: str, description: Optional[str] = None,
                     analyst_id: Optional[str] = None, notes: Optional[str] = None) -> Case:
        case_number = validate_case_number(case_number)
        existing = self.db.execute(select(Case).where(Case.case_number == case_number)).scalar_one_or_none()
        if existing:
            from app.utils.errors import ValidationAppError
            raise ValidationAppError("DUPLICATE_CASE_NUMBER", f"Case number '{case_number}' already exists.")
        case = Case(case_number=case_number, title=title, description=description,
                    analyst_id=analyst_id, notes=notes, status="open")
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def get_case(self, case_id: str) -> Case:
        case = self.db.get(Case, case_id)
        if not case:
            raise NotFoundError("Case", case_id)
        return case

    def list_cases(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Tuple[List[Case], int]:
        page, page_size = validate_pagination(page, page_size)
        query = select(Case)
        if status:
            query = query.where(Case.status == status)
        total = self.db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        rows = self.db.execute(
            query.order_by(Case.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(rows), total

    def update_case(self, case_id: str, **fields) -> Case:
        case = self.get_case(case_id)
        if "status" in fields and fields["status"] is not None:
            fields["status"] = validate_case_status(fields["status"])
        for key, value in fields.items():
            if value is not None and hasattr(case, key):
                setattr(case, key, value)
        self.db.commit()
        self.db.refresh(case)
        return case

    def archive_case(self, case_id: str) -> Case:
        return self.update_case(case_id, status="archived")

    def delete_case(self, case_id: str) -> None:
        case = self.get_case(case_id)
        self.db.delete(case)
        self.db.commit()
