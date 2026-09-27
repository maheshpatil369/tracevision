# Architecture

## High-level flow

```
Frontend (React/Vite)
      |
      v
FastAPI (app/api/routes/*)
      |
      v
Service layer (app/services/*)   <-- business logic, validation, orchestration
      |
      +--> Repositories/ORM (app/models/*, SQLAlchemy)  --> SQLite/PostgreSQL
      |
      +--> Background jobs (app/workers/job_runner.py)  --> ThreadPoolExecutor
                |
                v
        AnalysisOrchestrator (app/services/analysis_orchestrator.py)
                |
      +---------+----------+-----------+
      |         |          |           |
      v         v          v           v
  app/cv/*   app/cv/*   app/cv/*   app/ml/*
  video_io   detector   face_mesh  classifier
  tracker    geometry
                |
                v
        app/reporting/pdf_report.py (ReportLab)
```

## Layering rules

- **API routes** (`app/api/routes/`) only: parse the request, call exactly one
  service method, translate the result/exception into an HTTP response. No
  business logic lives here.
- **Services** (`app/services/`) contain all business logic and validation,
  and are the only layer that touches both the ORM and the CV/ML modules.
  Services never import FastAPI.
- **CV/ML/reporting modules** (`app/cv/`, `app/ml/`, `app/reporting/`) are
  pure Python — no FastAPI, no SQLAlchemy imports. This is what makes them
  independently unit-testable (see `backend/tests/`) without a running
  database or web server.
- **Models** (`app/models/`) are SQLAlchemy ORM classes only; `to_dict()`
  methods on each model are the single source of truth for the model's public
  JSON shape, used both by API responses and by report generation.

## The video-analysis pipeline

Implemented end-to-end in `app/services/analysis_orchestrator.py`:

```
UPLOAD -> METADATA -> FRAME EXTRACTION -> OBJECT DETECTION -> OBJECT TRACKING
   -> FACE DETECTION (for person tracks) -> 468 LANDMARKS -> 3D REPRESENTATION
   -> GEOMETRIC FEATURES -> EVIDENCE CAPTURE -> TIMELINE -> DB PERSISTENCE
   -> [ON DEMAND] REPORT GENERATION
```

Each stage updates a `ProcessingJob` row (`current_stage`, `progress_percent`)
so the frontend polls real progress rather than a fake animated bar.

## Background processing

A `ThreadPoolExecutor` (see `app/workers/job_runner.py`) runs analysis jobs
off the request thread. This was chosen over Celery/RQ specifically so the
project has **no external broker dependency** (no Redis/RabbitMQ needed) and
still works out of the box after `pip install -r requirements.txt` — see
`docs/architecture-decisions.md` for the trade-off this implies.

## Detector/tracker/facial-model abstraction

`app/cv/detector.py`, `app/cv/tracker.py`, and `app/cv/face_mesh.py` each
define a small interface (`ObjectDetector`, `Tracker`, `FaceLandmarker`) so
the orchestrator never depends on a specific vendor implementation. When the
preferred implementation (YOLO, ByteTrack, MediaPipe's model asset) is
unavailable, each module degrades to an explicitly-labeled fallback rather
than silently producing fabricated results — see `docs/limitations.md`.
