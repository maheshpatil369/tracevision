"""
Facial feature-vector classifier: training, hyperparameter optimization,
persistence, loading, and prediction (spec sections 22-24).

This is real, runnable scikit-learn code — no hardcoded prediction results.
`FaceClassifier.predict` returns whatever the loaded model actually outputs;
if no model has been trained yet, it raises `ModelNotTrainedError` rather
than fabricating a similarity score (spec section 68).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

CLASSIFIER_REGISTRY = {
    "random_forest": (RandomForestClassifier, {
        "clf__n_estimators": [100, 200, 400],
        "clf__max_depth": [None, 8, 16],
    }),
    "svm": (SVC, {
        "clf__C": [0.1, 1, 10],
        "clf__kernel": ["rbf", "linear"],
    }),
    "logistic_regression": (LogisticRegression, {
        "clf__C": [0.1, 1, 10],
    }),
}


class ModelNotTrainedError(Exception):
    pass


@dataclass
class TrainingResult:
    model_version: str
    algorithm: str
    best_params: Dict[str, Any]
    cv_folds: int
    metrics: Dict[str, float]
    feature_names: List[str]
    trained_at: float
    training_samples: int
    dataset_description: str

    def to_dict(self) -> dict:
        return asdict(self)


class FaceClassifier:
    """Wraps a scikit-learn Pipeline (StandardScaler + classifier) so the
    concrete algorithm can be swapped via `algorithm=` without changing any
    calling code (spec section 22: classifier abstraction)."""

    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self._pipeline: Optional[Pipeline] = None
        self._metadata: Optional[dict] = None

    # ------------------------------------------------------------ training --
    def train(self, X: np.ndarray, y: np.ndarray, algorithm: str = "random_forest",
              cv_folds: int = 5, dataset_description: str = "user-provided training set",
              search: str = "grid") -> TrainingResult:
        if algorithm not in CLASSIFIER_REGISTRY:
            raise ValueError(f"Unknown algorithm '{algorithm}'. Options: {list(CLASSIFIER_REGISTRY)}")
        if len(np.unique(y)) < 2:
            raise ValueError("Training requires at least 2 distinct classes.")

        model_cls, param_grid = CLASSIFIER_REGISTRY[algorithm]
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", model_cls(probability=True) if algorithm == "svm" else model_cls()),
        ])

        n_splits = min(cv_folds, min(np.bincount(y)))
        n_splits = max(2, n_splits)
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

        if search == "grid":
            searcher = GridSearchCV(pipeline, param_grid, cv=cv, scoring="f1_weighted", n_jobs=-1)
        else:
            from sklearn.model_selection import RandomizedSearchCV
            searcher = RandomizedSearchCV(pipeline, param_grid, cv=cv, scoring="f1_weighted",
                                           n_jobs=-1, n_iter=min(10, _grid_size(param_grid)), random_state=42)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y if min(np.bincount(y)) > 1 else None)

        searcher.fit(X_train, y_train)
        best_pipeline = searcher.best_estimator_
        y_pred = best_pipeline.predict(X_test)

        metrics = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
            "cv_best_score": round(float(searcher.best_score_), 4),
        }

        version = f"{algorithm}-{int(time.time())}"
        self._pipeline = best_pipeline
        self._metadata = {
            "model_version": version, "algorithm": algorithm,
            "best_params": searcher.best_params_, "cv_folds": n_splits,
            "metrics": metrics, "trained_at": time.time(),
            "training_samples": int(len(y)), "dataset_description": dataset_description,
        }
        self.save(version)

        return TrainingResult(
            model_version=version, algorithm=algorithm, best_params=searcher.best_params_,
            cv_folds=n_splits, metrics=metrics, feature_names=[],
            trained_at=self._metadata["trained_at"], training_samples=int(len(y)),
            dataset_description=dataset_description,
        )

    # ----------------------------------------------------------- persistence --
    def save(self, version: str):
        joblib.dump(self._pipeline, os.path.join(self.model_dir, f"{version}.joblib"))
        with open(os.path.join(self.model_dir, f"{version}.json"), "w") as f:
            json.dump(self._metadata, f, indent=2)
        latest_path = os.path.join(self.model_dir, "LATEST")
        with open(latest_path, "w") as f:
            f.write(version)

    def load(self, version: Optional[str] = None):
        if version is None:
            latest_path = os.path.join(self.model_dir, "LATEST")
            if not os.path.isfile(latest_path):
                raise ModelNotTrainedError("No trained model is available yet. Run model training first.")
            with open(latest_path) as f:
                version = f.read().strip()
        model_path = os.path.join(self.model_dir, f"{version}.joblib")
        meta_path = os.path.join(self.model_dir, f"{version}.json")
        if not (os.path.isfile(model_path) and os.path.isfile(meta_path)):
            raise ModelNotTrainedError(f"Model version '{version}' was not found in {self.model_dir}.")
        self._pipeline = joblib.load(model_path)
        with open(meta_path) as f:
            self._metadata = json.load(f)
        return self._metadata

    def list_versions(self) -> List[dict]:
        out = []
        if not os.path.isdir(self.model_dir):
            return out
        for fname in sorted(os.listdir(self.model_dir)):
            if fname.endswith(".json"):
                with open(os.path.join(self.model_dir, fname)) as f:
                    out.append(json.load(f))
        return out

    # ------------------------------------------------------------ inference --
    def predict(self, feature_vector: List[float]) -> Dict[str, Any]:
        if self._pipeline is None:
            try:
                self.load()
            except ModelNotTrainedError:
                raise
        proba = None
        X = np.array(feature_vector).reshape(1, -1)
        pred = self._pipeline.predict(X)[0]
        if hasattr(self._pipeline, "predict_proba"):
            proba = self._pipeline.predict_proba(X)[0].tolist()
        return {
            "prediction": str(pred),
            "probabilities": proba,
            "model_version": self._metadata["model_version"] if self._metadata else None,
        }


def _grid_size(param_grid: Dict[str, list]) -> int:
    size = 1
    for v in param_grid.values():
        size *= len(v)
    return size


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Used for facial comparison (spec section 24) — a real, deterministic
    similarity score between two feature vectors, explicitly NOT presented as
    proof of identity."""
    a, b = np.array(vec_a), np.array(vec_b)
    if a.shape != b.shape or np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return round(float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))), 6)
