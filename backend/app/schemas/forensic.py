from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class FacialComparisonCreate(BaseModel):
    face_id: str
    reference_face_id: Optional[str] = None
    reference_label: Optional[str] = None
    analyst_notes: Optional[str] = None


class ModelTrainRequest(BaseModel):
    algorithm: str = "random_forest"  # random_forest | svm | logistic_regression
    cv_folds: int = 5
    search: str = "grid"  # grid | random
    dataset_description: str = "user-provided training set"
    # Training samples: list of {feature_vector: [...], label: "..."}
    samples: List[dict]


class ReportGenerateRequest(BaseModel):
    analysis_id: str
    demo_mode: bool = False
