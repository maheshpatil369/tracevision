# models/

Downloaded model assets live here (never committed to version control):

- `yolov8n.pt` — YOLOv8 nano object-detection weights. Fetched by
  `python scripts/download_models.py`, or automatically by `ultralytics` on
  first use if you skip that step.
- `face_landmarker.task` — MediaPipe FaceLandmarker bundle (468-point face
  mesh). Fetched by the same script from Google's model storage.
- `classifiers/` — trained scikit-learn classifier versions produced by
  `POST /api/models/train` (joblib + JSON metadata pairs, plus a `LATEST`
  pointer file).

If a file listed above is missing, TRACEVISION does not fabricate its
output: object detection falls back to `FallbackMotionDetector`, and facial
landmark analysis is skipped and reported as unavailable until the model is
downloaded. See docs/limitations.md.
