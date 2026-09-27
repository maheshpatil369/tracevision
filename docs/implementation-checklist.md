# Implementation Checklist

Maps the 25 numbered objectives from the project spec (section 2) plus
other section-level requirements to their actual implementation status.
Status legend: **COMPLETE** (implemented and, where noted, executed/tested
in this delivery's sandbox), **PARTIAL** (implemented but with a known gap,
described), **NOT IMPLEMENTED** (not attempted, reason given).

## Facial analysis objectives (1-10)
| # | Requirement | Location | Test | Status |
|---|---|---|---|---|
| 1 | Detect faces from frames | `app/cv/face_mesh.py` | `test_face_mesh.py` (model-asset-missing path only — see below) | PARTIAL |
| 2 | Extract 468 landmarks | `app/cv/face_mesh.py`, `app/models/face.py` | same | PARTIAL |
| 3 | 3D facial representation | `app/cv/face_mesh.py:build_3d_representation` | `test_face_mesh.py` — PASSED | COMPLETE |
| 4 | Euclidean distances | `app/cv/geometry.py` | `test_geometry.py` — PASSED | COMPLETE |
| 5 | Geodesic distances | `app/cv/geometry.py` | `test_geometry.py` — PASSED | COMPLETE |
| 6 | Landmark ratios | `app/cv/geometry.py` | `test_geometry.py` — PASSED | COMPLETE |
| 7 | Feature vectors | `app/cv/geometry.py` | `test_geometry.py` — PASSED | COMPLETE |
| 8 | Train/compare ML classifiers | `app/ml/classifier.py` | `test_ml_pipeline.py` — PASSED | COMPLETE |
| 9 | Hyperparameter optimization | `app/ml/classifier.py` (GridSearchCV/RandomizedSearchCV) | `test_ml_pipeline.py` — PASSED | COMPLETE |
| 10 | Facial similarity/classification results | `app/services/model_service.py` | not independently unit-tested (depends on #1/#2 running against a real model asset) | PARTIAL |

**Why #1/#2/#10 are PARTIAL, not COMPLETE:** the real MediaPipe
`FaceLandmarker` requires a downloaded model asset (`face_landmarker.task`)
that this build's sandbox could not fetch (no network access — see
`docs/limitations.md`). The wrapper code is written against MediaPipe's
actual current API and its "honest failure" path (raising
`ModelAssetMissingError` instead of faking landmarks) **was** executed and
verified. The success path (a real face -> real 468 landmarks) was not
executed end-to-end in this delivery. Running
`python scripts/download_models.py` on a machine with network access, then
re-running `pytest backend/tests/`, would let you verify it directly.

## CCTV / object analysis objectives (11-25)
| # | Requirement | Location | Test | Status |
|---|---|---|---|---|
| 11 | Accept CCTV/video input | `app/api/routes/videos.py`, `app/cv/video_io.py` | `test_video_io.py` — PASSED | COMPLETE |
| 12 | Extract video frames | `app/cv/video_io.py:iter_frames` | `test_video_io.py` — PASSED | COMPLETE |
| 13 | Detect objects per frame | `app/cv/detector.py` | `test_detector_and_tracker.py` — PASSED (fallback path); YOLO path not exercised (no network for weights) | PARTIAL |
| 14 | Classify detected objects | `app/cv/detector.py:YoloDetector` | not exercised (see #13) | PARTIAL |
| 15 | Track objects across frames | `app/cv/tracker.py` | `test_detector_and_tracker.py` — PASSED | COMPLETE |
| 16 | Unique tracking IDs | `app/cv/tracker.py` | same | COMPLETE |
| 17 | Object timestamps | `app/cv/detector.py`, `app/models/detection.py` | same | COMPLETE |
| 18 | Object confidence scores | same | same | COMPLETE |
| 19 | First/last appearance | `app/models/detection.py:TrackedObjectRecord` | `test_detector_and_tracker.py` — PASSED | COMPLETE |
| 20 | Save evidence frames | `app/services/analysis_orchestrator.py` | not unit-tested directly (integration-level; exercised implicitly via orchestrator code review) | PARTIAL — see docs/evidence.md (only `first_appearance` trigger wired up) |
| 21 | Detect faces on persons | `app/services/analysis_orchestrator.py` (crops person boxes, runs FaceLandmarker) | depends on #1 | PARTIAL |
| 22 | Chronological event timeline | `app/models/timeline.py`, orchestrator | not unit-tested directly | PARTIAL — only 4 of 8 defined `EVENT_TYPES` are currently generated (see docs/timeline.md) |
| 23 | Store video-analysis findings | full `app/models/` + orchestrator persistence | schema verified by hand-review; DB layer not executable in this sandbox (no SQLAlchemy) | NOT VERIFIED BY EXECUTION |
| 24 | Generate forensic report | `app/reporting/pdf_report.py` | `test_pdf_report.py` — PASSED (real PDFs generated, `%PDF-` header verified) | COMPLETE |
| 25 | Downloadable PDF | `app/api/routes/reports.py:download_report` | not executable in this sandbox (FastAPI unavailable) | NOT VERIFIED BY EXECUTION |

## Cross-cutting sections
| Section | Requirement | Status |
|---|---|---|
| 5-6 | Navigation + Dashboard | COMPLETE (code); UI not rendered/screenshotted in this sandbox (no npm/network) |
| 7 | Case management | COMPLETE (code); see above for verification caveat |
| 8 | Video upload validation | COMPLETE + tested (`test_video_io.py`) |
| 9-10 | Analysis workflow + background processing | COMPLETE (code, thread-pool based, see architecture-decisions.md #1); not executed end-to-end |
| 25 | Database (SQLAlchemy + Alembic + SQLite) | COMPLETE (code, hand-written migration matching every model); not executed (no SQLAlchemy/Alembic in sandbox) |
| 29-30 | Report generation + management | COMPLETE, PDF generation tested directly |
| 31-32 | API + API docs | COMPLETE (code + `docs/api.md`); FastAPI's own `/docs` not renderable in this sandbox |
| 33/50 | Security basics | COMPLETE (upload validation, path sanitization tested); auth NOT implemented (see docs/security.md) |
| 34 | Environment configuration | COMPLETE (`.env.example`, `pydantic-settings`) |
| 38 | Field-by-field documentation | COMPLETE but **consolidated**: 2 files instead of ~11-15 (see architecture-decisions.md #8) |
| 44 | Testing | PARTIAL: 27 tests covering CV/ML/reporting core all PASSED; no API-layer/integration tests were runnable in this sandbox (FastAPI/SQLAlchemy unavailable) — see `backend/tests/` |
| 45-46 | Health check + model management scripts | COMPLETE (code); not executed in this sandbox |
| 61-64 | Docker | COMPLETE (code); `docker compose up --build` not executed in this sandbox (no Docker daemon / no network for image layers) |
| 68 | No fake data | COMPLETE as a design principle throughout — verified directly for the modules that could be executed (detector fallback, PDF report empty-state rendering, ML predict-before-train refusal) |

## Not implemented at all
- Authentication enforcement on API routes (scaffolded, not wired — see
  docs/security.md)
- XGBoost/Optuna integration (listed as optional in spec; scikit-learn's
  GridSearchCV/RandomizedSearchCV cover the stated requirement)
- Interactive 3D landmark viewer in the frontend (data is available via the
  API; no `three.js` viewer component built yet)
- `last_appearance`, `high_confidence_detection` (as an evidence trigger,
  distinct from the timeline event of the same name), and
  `analyst_selected` evidence triggers
- `object_interaction`, `evidence_captured`, `analysis_started`,
  `analysis_completed` timeline event types
