from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.forensic import FacialComparisonCreate, ModelTrainRequest
from app.services.model_service import ModelService
from app.utils.errors import AppError

router = APIRouter(prefix="/api/models", tags=["models"])


@router.post("/train")
def train_model(payload: ModelTrainRequest, db: Session = Depends(get_db)):
    try:
        model_run = ModelService(db).train(
            samples=payload.samples, algorithm=payload.algorithm, cv_folds=payload.cv_folds,
            search=payload.search, dataset_description=payload.dataset_description,
        )
        return {"success": True, "data": model_run.to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.get("")
def list_models(db: Session = Depends(get_db)):
    rows = ModelService(db).list_models()
    return {"success": True, "data": [r.to_dict() for r in rows]}


@router.post("/compare")
def compare_faces(payload: FacialComparisonCreate, db: Session = Depends(get_db)):
    try:
        comparison = ModelService(db).compare_faces(**payload.model_dump())
        return {"success": True, "data": comparison.to_dict()}
    except AppError as e:
        raise e.to_http_exception()
