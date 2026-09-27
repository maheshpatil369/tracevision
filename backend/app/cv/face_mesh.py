"""
Face detection + 468-point facial landmark extraction using MediaPipe's
FaceLandmarker (Tasks API, mediapipe >= 0.10), and construction of a 3D
facial representation from the landmark cloud.

MediaPipe's modern Tasks API requires a downloaded model asset file
(`face_landmarker.task`, a few MB) — see `scripts/download_models.py`. That
file is topology/weights data, not something this code can fabricate, so
when it is missing `FaceLandmarker.__init__` raises a clear
`ModelAssetMissingError` rather than silently degrading into a fake detector.

This wraps mediapipe behind a small, testable interface (`FaceLandmarker` in
this module — distinct from `mediapipe.tasks...vision.FaceLandmarker`) so the
rest of the application never imports mediapipe directly.

Honest failure modes (per spec section 17): no face, multiple faces, low
detection confidence, and partial/occluded faces are all represented
explicitly in `FaceDetectionResult` rather than silently faked.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.tasks.python.core.base_options import BaseOptions
    _MEDIAPIPE_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only when mediapipe is absent
    _MEDIAPIPE_AVAILABLE = False

NUM_LANDMARKS = 468
DEFAULT_MODEL_FILENAME = "face_landmarker.task"


class ModelAssetMissingError(RuntimeError):
    pass


@dataclass
class FaceDetectionResult:
    face_found: bool
    num_faces: int
    landmarks: Optional[np.ndarray]      # (468, 3) normalized x,y,z or None
    landmark_confidence: Optional[float]  # heuristic, see _estimate_confidence
    bbox: Optional[dict]                  # {x,y,width,height} normalized 0..1
    quality_flags: List[str] = field(default_factory=list)  # e.g. "low_confidence", "multiple_faces"

    def to_dict(self) -> dict:
        return {
            "face_found": self.face_found,
            "num_faces": self.num_faces,
            "landmarks": None if self.landmarks is None else self.landmarks.tolist(),
            "landmark_confidence": self.landmark_confidence,
            "bbox": self.bbox,
            "quality_flags": self.quality_flags,
        }


class FaceLandmarker:
    """Stateful wrapper around MediaPipe's FaceLandmarker task. Create one
    instance per video-processing job and reuse it across frames (model
    reuse — see spec section 47 Performance) rather than re-initializing
    per frame."""

    def __init__(self, model_dir: str = "models", model_filename: str = DEFAULT_MODEL_FILENAME,
                 max_num_faces: int = 3, min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5, running_mode: str = "IMAGE"):
        if not _MEDIAPIPE_AVAILABLE:
            raise RuntimeError(
                "mediapipe is not installed. Facial landmark analysis is unavailable "
                "until `pip install mediapipe` succeeds. See docs/troubleshooting.md."
            )
        model_path = os.path.join(model_dir, model_filename)
        if not os.path.isfile(model_path):
            raise ModelAssetMissingError(
                f"Facial landmark model asset not found at '{model_path}'. Run "
                f"`python scripts/download_models.py` first. Facial analysis cannot "
                f"produce real results without this file \u2014 no fallback is used here "
                f"because faked 468-point landmarks would violate the no-fake-data "
                f"requirement (spec section 68)."
            )
        mode = mp_vision.RunningMode.VIDEO if running_mode.upper() == "VIDEO" else mp_vision.RunningMode.IMAGE
        options = mp_vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=mode,
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        self._mode = mode
        self._mp = mp
        self._frame_index = 0

    def close(self):
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @staticmethod
    def _estimate_confidence(landmarks_2d: np.ndarray, frame_shape: tuple) -> float:
        """MediaPipe's FaceLandmarker does not return a single scalar
        face-quality score for the mesh itself, so we derive a conservative
        heuristic confidence from how much of the landmark cloud falls
        inside the visible frame (a proxy for occlusion/cropping) — NOT a
        substitute for the task's own detection-confidence threshold, which
        gates whether a face is reported at all."""
        h, w = frame_shape[:2]
        in_bounds = np.mean(
            (landmarks_2d[:, 0] >= 0) & (landmarks_2d[:, 0] <= w) &
            (landmarks_2d[:, 1] >= 0) & (landmarks_2d[:, 1] <= h)
        )
        return round(float(in_bounds), 4)

    def process(self, frame_bgr: np.ndarray, timestamp_ms: Optional[int] = None) -> FaceDetectionResult:
        import cv2
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)

        if self._mode == mp_vision.RunningMode.VIDEO:
            ts = timestamp_ms if timestamp_ms is not None else self._frame_index * 33
            result = self._landmarker.detect_for_video(mp_image, ts)
            self._frame_index += 1
        else:
            result = self._landmarker.detect(mp_image)

        h, w = frame_bgr.shape[:2]

        if not result.face_landmarks:
            return FaceDetectionResult(
                face_found=False, num_faces=0, landmarks=None,
                landmark_confidence=None, bbox=None, quality_flags=["no_face_detected"],
            )

        num_faces = len(result.face_landmarks)
        flags: List[str] = []
        if num_faces > 1:
            flags.append("multiple_faces")

        # Use the largest face (by bbox area) as the primary subject.
        best_pts, best_area = None, -1.0
        for face_landmarks in result.face_landmarks:
            pts = np.array([[lm.x * w, lm.y * h] for lm in face_landmarks])
            x0, y0 = pts.min(axis=0)
            x1, y1 = pts.max(axis=0)
            area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
            if area > best_area:
                best_area = area
                best_pts = face_landmarks

        pts3d = np.array([[lm.x, lm.y, lm.z] for lm in best_pts], dtype=np.float64)
        pts2d_px = pts3d[:, :2] * np.array([w, h])
        confidence = self._estimate_confidence(pts2d_px, frame_bgr.shape)

        if confidence < 0.85:
            flags.append("partial_face_or_cropped")
        if pts3d.shape[0] < NUM_LANDMARKS:
            flags.append("incomplete_landmark_set")  # defensive

        x0, y0 = pts2d_px.min(axis=0)
        x1, y1 = pts2d_px.max(axis=0)
        bbox = {
            "x": round(float(x0 / w), 6), "y": round(float(y0 / h), 6),
            "width": round(float((x1 - x0) / w), 6), "height": round(float((y1 - y0) / h), 6),
        }

        # FaceLandmarker's default model returns 478 points when iris
        # refinement is included; we keep exactly the canonical 468-point
        # tessellation index space so downstream geometry code (which is
        # keyed to those indices) is stable regardless of iris output.
        landmarks_468 = pts3d[:NUM_LANDMARKS]

        return FaceDetectionResult(
            face_found=True, num_faces=num_faces, landmarks=landmarks_468,
            landmark_confidence=confidence, bbox=bbox, quality_flags=flags,
        )


def build_3d_representation(landmarks: np.ndarray) -> dict:
    """Derives a 3D facial representation directly from the actual landmark
    coordinates (spec section 19) — centered and scale-normalized so different
    faces/frames are comparable, with NO synthetic points added."""
    if landmarks is None:
        return {"points": [], "centroid": None, "scale": None}
    centroid = landmarks.mean(axis=0)
    centered = landmarks - centroid
    scale = float(np.linalg.norm(centered, axis=1).mean()) or 1.0
    normalized = centered / scale
    return {
        "points": normalized.tolist(),
        "centroid": centroid.tolist(),
        "scale": scale,
        "point_count": int(landmarks.shape[0]),
    }
