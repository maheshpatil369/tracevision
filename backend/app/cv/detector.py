"""
Object detection abstraction (spec section 12).

`ObjectDetector` is the interface the rest of the app depends on so the app
is never tightly coupled to a specific model implementation. Two concrete
implementations are provided:

  - YoloDetector: real detection via Ultralytics YOLO, used when the
    `ultralytics` package AND a model weights file are both available.
  - FallbackMotionDetector: an honest, clearly-labeled degraded mode that
    uses OpenCV background subtraction (MOG2) + contour boxes to produce
    *motion-region* boxes when no trained model is installed. It NEVER
    claims a class label the model didn't actually predict — every result
    it returns is tagged `detector_backend="motion_fallback"` and
    class_name is always "moving_object" (spec section 68: no fake data).

Do not call this a full object-classification system when running in
fallback mode — see docs/limitations.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

try:
    from ultralytics import YOLO
    _ULTRALYTICS_AVAILABLE = True
except Exception:  # pragma: no cover
    _ULTRALYTICS_AVAILABLE = False

# Classes explicitly called out in the spec (section 12) that COCO-pretrained
# YOLO models support out of the box. This list is documentation only — it is
# NEVER used to invent a detection; it is shown in the UI/docs as "the classes
# the default model can recognize".
SUPPORTED_CLASSES_DOC = [
    "person", "car", "bus", "truck", "motorcycle", "bicycle",
    "backpack", "handbag", "suitcase", "cell phone", "laptop",
]


@dataclass
class Detection:
    frame_number: int
    timestamp: float
    class_id: int
    class_name: str
    confidence: float
    x: float
    y: float
    width: float
    height: float
    detector_backend: str

    @property
    def center(self) -> tuple:
        return (self.x + self.width / 2, self.y + self.height / 2)

    def to_dict(self) -> dict:
        cx, cy = self.center
        return {
            "frame_number": self.frame_number, "timestamp": round(self.timestamp, 3),
            "class_id": self.class_id, "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": {"x": self.x, "y": self.y, "width": self.width, "height": self.height},
            "center": {"x": cx, "y": cy}, "detector_backend": self.detector_backend,
        }


class ObjectDetector:
    """Common interface. `detect(frame, frame_number, timestamp) -> List[Detection]`."""

    backend_name: str = "abstract"

    def detect(self, frame: np.ndarray, frame_number: int, timestamp: float,
               confidence_threshold: float = 0.4, iou_threshold: float = 0.5,
               max_detections: int = 50) -> List[Detection]:
        raise NotImplementedError


class YoloDetector(ObjectDetector):
    backend_name = "yolo"

    def __init__(self, weights_path: str):
        if not _ULTRALYTICS_AVAILABLE:
            raise RuntimeError(
                "ultralytics is not installed. Run `pip install ultralytics` and "
                "`python scripts/download_models.py` to enable real object detection."
            )
        self._model = YOLO(weights_path)
        self.class_names = self._model.names

    def detect(self, frame: np.ndarray, frame_number: int, timestamp: float,
               confidence_threshold: float = 0.4, iou_threshold: float = 0.5,
               max_detections: int = 50) -> List[Detection]:
        results = self._model.predict(
            frame, conf=confidence_threshold, iou=iou_threshold,
            max_det=max_detections, verbose=False,
        )
        out: List[Detection] = []
        if not results:
            return out
        r = results[0]
        for box in r.boxes:
            xyxy = box.xyxy[0].tolist()
            x0, y0, x1, y1 = xyxy
            cls_id = int(box.cls[0])
            out.append(Detection(
                frame_number=frame_number, timestamp=timestamp, class_id=cls_id,
                class_name=self.class_names.get(cls_id, str(cls_id)),
                confidence=float(box.conf[0]), x=float(x0), y=float(y0),
                width=float(x1 - x0), height=float(y1 - y0), detector_backend=self.backend_name,
            ))
        return out


class FallbackMotionDetector(ObjectDetector):
    """Background-subtraction based motion-region detector used only when no
    trained object-detection model is installed. This is explicitly a
    reduced-capability development fallback, not a replacement for YOLO."""

    backend_name = "motion_fallback"

    def __init__(self, min_area_px: int = 900):
        import cv2
        self._cv2 = cv2
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=40, detectShadows=True)
        self.min_area_px = min_area_px
        self._warmed_up_frames = 0

    def detect(self, frame: np.ndarray, frame_number: int, timestamp: float,
               confidence_threshold: float = 0.4, iou_threshold: float = 0.5,
               max_detections: int = 50) -> List[Detection]:
        cv2 = self._cv2
        fg_mask = self._bg_subtractor.apply(frame)
        self._warmed_up_frames += 1
        # Background model needs a short warm-up before contours are meaningful.
        if self._warmed_up_frames < 5:
            return []
        _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections: List[Detection] = []
        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:max_detections]:
            area = cv2.contourArea(c)
            if area < self.min_area_px:
                continue
            x, y, w, h = cv2.boundingRect(c)
            frame_area = frame.shape[0] * frame.shape[1]
            # Confidence here is a bounded heuristic proportional to relative
            # motion-region size, NOT a model's predicted probability — this is
            # clearly documented and surfaced in the UI as a fallback signal.
            heuristic_conf = float(min(0.6, 0.15 + (area / frame_area) * 4))
            if heuristic_conf < confidence_threshold:
                continue
            detections.append(Detection(
                frame_number=frame_number, timestamp=timestamp, class_id=-1,
                class_name="moving_object", confidence=heuristic_conf,
                x=float(x), y=float(y), width=float(w), height=float(h),
                detector_backend=self.backend_name,
            ))
        return detections


def build_default_detector(weights_path: Optional[str]) -> ObjectDetector:
    """Factory used by the analysis orchestrator. Prefers YOLO when both the
    library and weights are available; otherwise falls back honestly."""
    import os
    if weights_path and os.path.isfile(weights_path) and _ULTRALYTICS_AVAILABLE:
        try:
            return YoloDetector(weights_path)
        except Exception:
            pass
    return FallbackMotionDetector()
