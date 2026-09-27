from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin


class Face(Base, UUIDPKMixin, TimestampMixin):
    """A single detected face instance at a point in time (spec sections
    17-21). Landmarks/features are stored as JSON since they are fixed-size
    numeric arrays, not relational data that benefits from further
    normalization; see docs/database.md for the rationale."""
    __tablename__ = "faces"

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), nullable=False)
    analysis: Mapped["Analysis"] = relationship(back_populates="faces")

    track_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tracked_objects.id"), nullable=True)
    track: Mapped[Optional["TrackedObjectRecord"]] = relationship(back_populates="faces")

    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    face_found: Mapped[bool] = mapped_column(nullable=False, default=True)
    num_faces_in_frame: Mapped[int] = mapped_column(Integer, default=1)
    landmark_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_flags: Mapped[list] = mapped_column(JSON, default=list)
    bbox: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Full 468x3 landmark set (spec section 18)
    landmarks: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    landmark_model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 3D representation (spec section 19)
    representation_3d: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Geometric features: Euclidean/geodesic/ratios/vector (spec sections 20-21)
    geometric_features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    feature_set_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    faces_compared: Mapped[list["FacialComparison"]] = relationship(
        back_populates="face", foreign_keys="FacialComparison.face_id", cascade="all, delete-orphan")

    def to_dict(self, include_landmarks: bool = False) -> dict:
        d = {
            "id": self.id, "analysis_id": self.analysis_id, "track_id": self.track_id,
            "frame_number": self.frame_number, "timestamp": round(self.timestamp_seconds, 3),
            "face_found": self.face_found, "num_faces_in_frame": self.num_faces_in_frame,
            "landmark_confidence": self.landmark_confidence, "quality_flags": self.quality_flags,
            "bbox": self.bbox, "representation_3d_summary": {
                "point_count": (self.representation_3d or {}).get("point_count"),
                "scale": (self.representation_3d or {}).get("scale"),
            } if self.representation_3d else None,
            "geometric_features": self.geometric_features,
            "feature_set_version": self.feature_set_version,
        }
        if include_landmarks:
            d["landmarks"] = self.landmarks
            d["representation_3d"] = self.representation_3d
        return d


class ModelRun(Base, UUIDPKMixin, TimestampMixin):
    """One trained classifier version and its evaluation metrics
    (spec sections 22-23, 57). Never contains invented metrics — a field is
    left null (rendered as 'Not available') rather than guessed."""
    __tablename__ = "model_runs"

    model_version: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    best_params: Mapped[dict] = mapped_column(JSON, default=dict)
    cv_folds: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    training_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_description: Mapped[str] = mapped_column(String(255), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "model_version": self.model_version, "algorithm": self.algorithm,
            "best_params": self.best_params, "cv_folds": self.cv_folds,
            "accuracy": self.accuracy if self.accuracy is not None else "Not available",
            "precision": self.precision if self.precision is not None else "Not available",
            "recall": self.recall if self.recall is not None else "Not available",
            "f1_score": self.f1_score if self.f1_score is not None else "Not available",
            "training_samples": self.training_samples, "dataset_description": self.dataset_description,
            "trained_at": self.created_at.isoformat(),
        }


class FacialComparison(Base, UUIDPKMixin, TimestampMixin):
    """Analyst-initiated comparison between two faces (spec section 24)."""
    __tablename__ = "facial_comparisons"

    face_id: Mapped[str] = mapped_column(ForeignKey("faces.id"), nullable=False)
    face: Mapped["Face"] = relationship(back_populates="faces_compared", foreign_keys=[face_id])

    reference_face_id: Mapped[Optional[str]] = mapped_column(ForeignKey("faces.id"), nullable=True)
    reference_label: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)  # e.g. external reference image name

    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    classifier_prediction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    classifier_probabilities: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    model_version_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    analyst_notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "face_id": self.face_id, "reference_face_id": self.reference_face_id,
            "reference_label": self.reference_label,
            "similarity_score": self.similarity_score if self.similarity_score is not None else "Not available",
            "classifier_prediction": self.classifier_prediction or "No facial comparison available.",
            "classifier_probabilities": self.classifier_probabilities,
            "model_version_used": self.model_version_used,
            "analyst_notes": self.analyst_notes,
            "created_at": self.created_at.isoformat(),
        }
