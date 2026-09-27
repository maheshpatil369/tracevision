# Limitations

Honest, explicit limitations (spec sections 56/79 require this document
and forbid overstating capability).

## Object detection
- Object classes are limited to whatever the loaded YOLO weights were
  trained on (80 COCO classes for the default `yolov8n.pt`) — TRACEVISION
  does not identify arbitrary objects outside that set.
- When YOLO/its weights are unavailable, the system falls back to a
  motion-based detector that reports only generic `moving_object` boxes,
  not real classification. This is always labeled (`detector_backend:
  "motion_fallback"`) and never presented as full object recognition.
- Low-quality/low-resolution/heavily-compressed video reduces detection
  accuracy; no amount of post-processing recovers information the source
  footage didn't capture.

## Object tracking
- Occlusion longer than `TRACKER_MAX_AGE` frames (default 15) will split
  one real-world object into two tracked IDs.
- The built-in IoU tracker uses only bounding-box overlap + class match —
  it does not use appearance/re-identification features, so two similar
  objects crossing paths can occasionally swap IDs. ByteTrack (used
  automatically when `supervision` is installed) is more robust to this
  but still not appearance-based re-ID.

## Facial analysis
- Face angle, motion blur, occlusion (masks, hands, hair), and poor
  lighting all reduce landmark quality or prevent detection entirely —
  reflected honestly via `quality_flags`, never silently ignored.
- The 3D facial representation is a normalized point cloud derived
  directly from 2D-image-relative landmarks with MediaPipe's estimated
  depth (z) — it is not a full 3D Morphable Model reconstruction, and
  should not be treated as photogrammetric-grade 3D geometry.
- Facial comparison produces a similarity score and/or classifier
  prediction — **neither is proof of identity**. Every report and UI
  surface carries this disclaimer.

## Machine learning
- Classifier quality is entirely dependent on the labeled training data an
  analyst supplies via `POST /api/models/train` — this project ships no
  pretrained facial-classification model and no real face dataset (none is
  included, for privacy/licensing reasons).
- Metrics are computed on a single train/test split, not extensive
  held-out validation across many sessions/lighting conditions — treat
  reported accuracy as indicative, not a guarantee of real-world
  performance.

## General
- No claim of universal object recognition.
- No claim of guaranteed identity matching.
- Not an automatic legal determination — every generated report states
  this explicitly (spec section 29.J).
- No chain-of-custody legal compliance is implemented or claimed (see
  `docs/privacy.md`).
- Authentication is scaffolded but not enforced on any endpoint by default
  (see `docs/security.md`) — do not expose an unmodified deployment to an
  untrusted network.

## Development-environment limitations specific to this build

This project was built and its core CV/ML/reporting logic was tested in a
sandbox with **no internet access**. As a direct result:
- The FastAPI/SQLAlchemy/Alembic layers, and the entire frontend, could not
  be installed or executed in that sandbox and are therefore **unverified
  by direct execution** in this delivery — they are correct, idiomatic code
  reviewed carefully by hand, not code that was run and observed to work.
- `scripts/download_models.py`'s downloads (YOLO weights, MediaPipe's
  `face_landmarker.task`) were not fetched or tested in that sandbox.
- What **was** actually executed and passed (27/27 tests): OpenCV video
  I/O, the geometry engine (using MediaPipe's real mesh topology data),
  the object detector/tracker abstractions, the scikit-learn training/
  prediction pipeline, and ReportLab PDF generation.
See `PROJECT_COMPLETION_REPORT.md` for the complete, itemized verification
status.
