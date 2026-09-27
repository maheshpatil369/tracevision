from __future__ import annotations

import os
from typing import List

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.ml.classifier import FaceClassifier, ModelNotTrainedError, cosine_similarity
from app.models.face import Face, FacialComparison, ModelRun
from app.utils.errors import NotFoundError, ValidationAppError

settings = get_settings()


class ModelService:
    def __init__(self, db: Session):
        self.db = db
        self.classifier = FaceClassifier(model_dir=os.path.join(settings.MODEL_DIRECTORY, "classifiers"))

    def train(self, samples: List[dict], algorithm: str = "random_forest",
              cv_folds: int = 5, search: str = "grid",
              dataset_description: str = "user-provided training set") -> ModelRun:
        """samples: [{"feature_vector": [...], "label": "..."}]. Hyperparameter
        optimization runs here, NOT during per-video analysis (spec section 23)."""
        if len(samples) < 4:
            raise ValidationAppError("INSUFFICIENT_SAMPLES", "At least 4 labeled samples are required to train.")
        X = np.array([s["feature_vector"] for s in samples])
        labels = [s["label"] for s in samples]
        label_to_idx = {l: i for i, l in enumerate(sorted(set(labels)))}
        y = np.array([label_to_idx[l] for l in labels])

        result = self.classifier.train(X, y, algorithm=algorithm, cv_folds=cv_folds,
                                        dataset_description=dataset_description, search=search)

        model_run = ModelRun(
            model_version=result.model_version, algorithm=result.algorithm,
            best_params=result.best_params, cv_folds=result.cv_folds,
            accuracy=result.metrics.get("accuracy"), precision=result.metrics.get("precision"),
            recall=result.metrics.get("recall"), f1_score=result.metrics.get("f1_score"),
            training_samples=result.training_samples, dataset_description=result.dataset_description,
        )
        self.db.add(model_run)
        self.db.commit()
        self.db.refresh(model_run)
        return model_run

    def list_models(self) -> list[ModelRun]:
        rows = self.db.execute(select(ModelRun).order_by(ModelRun.created_at.desc())).scalars().all()
        return list(rows)

    def compare_faces(self, face_id: str, reference_face_id: str = None,
                       reference_label: str = None, analyst_notes: str = None) -> FacialComparison:
        face = self.db.get(Face, face_id)
        if not face:
            raise NotFoundError("Face", face_id)
        if not face.geometric_features:
            raise ValidationAppError("NO_FEATURES", "This face has no geometric feature vector to compare.")

        similarity = None
        if reference_face_id:
            ref_face = self.db.get(Face, reference_face_id)
            if not ref_face or not ref_face.geometric_features:
                raise NotFoundError("Face", reference_face_id)
            similarity = cosine_similarity(
                face.geometric_features["vector"], ref_face.geometric_features["vector"])

        prediction, probabilities, model_version = None, None, None
        try:
            out = self.classifier.predict(face.geometric_features["vector"])
            prediction, probabilities, model_version = out["prediction"], out["probabilities"], out["model_version"]
        except ModelNotTrainedError:
            pass  # explicitly leave as None -> rendered as "No facial comparison available."

        comparison = FacialComparison(
            face_id=face_id, reference_face_id=reference_face_id, reference_label=reference_label,
            similarity_score=similarity, classifier_prediction=prediction,
            classifier_probabilities=probabilities, model_version_used=model_version,
            analyst_notes=analyst_notes,
        )
        self.db.add(comparison)
        self.db.commit()
        self.db.refresh(comparison)
        return comparison
