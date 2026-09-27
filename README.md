# TRACEVISION: Intelligent Analysis of Visual Evidence

An AI-powered forensic video analysis system: upload CCTV/video footage,
detect and track objects, analyze visible faces with 468-point landmarks
and 3D geometric features, run ML-based facial comparison, automatically
build a chronological evidence timeline, and generate a downloadable
forensic PDF report.

**Read this first:** `PROJECT_COMPLETION_REPORT.md` states exactly what was
executed and verified during development versus what is correct, reviewed
code that could not be run in the build sandbox (which had no internet
access). `docs/limitations.md` and `docs/implementation-checklist.md` give
the same information in more detail.

## Problem being solved

Manually reviewing hours of CCTV footage for objects, people, and faces of
interest is slow and error-prone. TRACEVISION automates the mechanical
parts of that review — detection, tracking, facial landmark extraction,
geometric feature computation, and report drafting — while keeping a human
analyst in the loop for every interpretive judgment, and never presenting
a probabilistic ML output as a certain conclusion.

## Objectives

See `docs/implementation-checklist.md` for the full, spec-numbered mapping.
In short: object detection/classification/tracking with stable IDs,
timestamps and confidence; 468-point facial landmarks, 3D representation,
geometric features (Euclidean/geodesic/ratio/vector), ML classification
with hyperparameter optimization; evidence-frame capture; a chronological
timeline; and an automatically generated, honestly-labeled PDF report.

## Features

- Case management (create/update/archive/delete, video upload, per-case
  reports)
- Real video metadata extraction + safe upload handling
- Background (non-blocking) video analysis with live progress
- Object detection (YOLO, with an honestly-labeled motion-based fallback)
- Multi-object tracking (ByteTrack when available, built-in IoU tracker
  otherwise) with stable IDs, trajectories, and confidence statistics
- Face detection, 468-point landmarks, 3D representation, geometric
  features (Euclidean, geodesic, ratios, feature vectors) — all real,
  deterministic computation, no fabricated results
- scikit-learn classifier training with GridSearchCV/RandomizedSearchCV
  hyperparameter search, versioned model persistence
- Facial comparison (cosine similarity + classifier prediction), always
  labeled as analytical, never as identity proof
- Evidence-frame gallery and chronological event timeline
- Automated forensic PDF report generation (ReportLab), versioned, with a
  mandatory investigative-use disclaimer
- Dashboard with real aggregate statistics (nothing hardcoded)

## Architecture

See `docs/architecture.md` for the full diagram. Summary:
`React/Vite frontend -> FastAPI -> service layer -> (SQLAlchemy ORM |
OpenCV/MediaPipe/YOLO/tracker | scikit-learn | ReportLab)`, with a
thread-pool background worker running the video-analysis pipeline so API
requests never block on a long video.

## Technology stack

Backend: Python, FastAPI, SQLAlchemy, Alembic, SQLite (default).
Computer vision: OpenCV, MediaPipe (FaceLandmarker), Ultralytics YOLO,
ByteTrack (via `supervision`) with a built-in IoU-tracker fallback.
Machine learning: scikit-learn (GridSearchCV/RandomizedSearchCV), joblib.
Reporting: ReportLab. Frontend: React, TypeScript, Vite, Tailwind CSS.
Testing: pytest. See `docs/architecture-decisions.md` for every place this
deviates from the spec's suggested stack, and why.

## Requirements

Python 3.11+, Node.js 20+, ~2GB disk for models. No GPU required (CPU
inference is fully supported, just slower). See `docs/installation.md`.

## Installation

```bash
git clone <repo-url> tracevision && cd tracevision
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example backend/.env
python scripts/setup.py
python scripts/download_models.py     # needs internet access
python scripts/health_check.py
cd backend && uvicorn app.main:app --reload
```
In a second terminal:
```bash
cd frontend && npm install && npm run dev
```
Full details, Windows instructions, and Docker: `docs/installation.md`.

## Environment setup

All configuration is via environment variables — see `.env.example` and
`docs/deployment.md`'s pre-launch checklist. Every setting has a safe local
default.

## Model setup

`python scripts/download_models.py` fetches YOLOv8n weights and MediaPipe's
`face_landmarker.task`. If this step is skipped or fails (no network),
TRACEVISION still runs: object detection uses an honestly-labeled
motion-based fallback, and facial analysis is skipped and reported as
unavailable rather than faked. See `docs/limitations.md`.

## Database setup

`python scripts/setup.py` runs `alembic upgrade head` (falling back to
direct ORM table creation if Alembic isn't available). See `docs/database.md`
for the full schema.

## Backend / frontend startup

```bash
cd backend && uvicorn app.main:app --reload      # http://localhost:8000
cd frontend && npm run dev                        # http://localhost:5173
```

## Docker startup

```bash
docker compose up --build
```

## First-use guide

1. **Create a case** — Cases page -> "New case" (case number + title).
2. **Upload a video** — open the case -> "Upload video" (mp4/avi/mov/mkv/webm).
3. **Run analysis** — click "Start analysis" next to the uploaded video.
4. **Inspect objects** — Analysis Detail -> Objects tab (per-class summary
   table).
5. **Inspect faces** — Analysis Detail -> Faces tab (landmark confidence,
   quality flags, geometric features).
6. **Inspect evidence** — Analysis Detail -> Evidence tab (annotated
   frame gallery).
7. **View the timeline** — Analysis Detail -> Timeline tab (chronological
   events).
8. **Generate a report** — Analysis Detail -> Overview tab -> "Generate
   forensic report (PDF)".
9. **Download the PDF** — Case Detail -> Reports section -> "Download PDF".

## Project structure

```
TRACEVISION/
├── backend/        FastAPI app, CV/ML/reporting modules, tests, alembic
├── frontend/        React + TypeScript + Vite + Tailwind SPA
├── models/           (inside backend/) downloaded model assets — gitignored
├── data/             (inside backend/) uploads/processed/evidence/reports
├── docs/             architecture, API, per-feature, and field-reference docs
├── scripts/          setup, seed, download_models, health_check
├── Dockerfile / docker-compose.yml
└── PROJECT_COMPLETION_REPORT.md
```
See `docs/architecture.md` for the layering rationale.

## Testing

```bash
cd backend
pytest tests/ -v
```
27 tests cover the CV/ML/reporting core (video I/O, geometry, face-mesh
honest-failure paths, detector/tracker, ML training/prediction, PDF
generation) and passed during development. API-layer/integration tests
require `pip install -r requirements.txt` to succeed first (FastAPI/
SQLAlchemy) — see `PROJECT_COMPLETION_REPORT.md`.

## Health check

```bash
python scripts/health_check.py
```

## Troubleshooting

See `docs/troubleshooting.md`.

## Limitations

See `docs/limitations.md` — read this before relying on any output.

## Privacy

See `docs/privacy.md`. You are responsible for lawful handling of any CCTV
footage and biometric data this software processes.

## Forensic disclaimer

**The output is intended as investigative/decision-support evidence and is
not an automatic legal determination.** This disclaimer is printed on
every generated report.
