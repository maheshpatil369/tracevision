# Database

SQLite by default (`DATABASE_URL=sqlite:///./data/tracevision.db`); any
SQLAlchemy-supported database works by changing that one setting (e.g.
`postgresql+psycopg2://user:pass@host/db`). Schema is managed via Alembic
(`backend/alembic/versions/0001_initial.py`); `python scripts/setup.py`
runs `alembic upgrade head` automatically, or `app.database.init_db.init_db()`
creates tables directly from ORM metadata as a fallback.

Every primary key is a `String(36)` UUID (see `docs/architecture-decisions.md`
#5). Every table has `created_at`/`updated_at` (`TimestampMixin`).

## Tables and relationships

```
users --< cases --< videos --< analyses --< processing_jobs
                        |           |
                        |           +--< tracked_objects --< object_detections
                        |           |         |        \--< faces
                        |           |         |
                        |           +--< object_detections (FK track_id -> tracked_objects, nullable)
                        |           +--< faces (FK track_id -> tracked_objects, nullable)
                        |           |         \--< facial_comparisons
                        |           +--< evidence_frames
                        |           +--< timeline_events (FK -> tracked_objects, faces, evidence_frames)
                        |           +--< reports (FK -> cases too)
                        +--< reports

model_runs   (standalone: trained classifier versions, not FK'd to a case)
```

## Table-by-table

### `users`
Analyst accounts. `role` is `analyst` or `admin`. Passwords are hashed
(spec's optional-auth requirement); no plaintext credentials are ever
stored.

### `cases`
The forensic case. `case_number` is the human-facing unique identifier
(`CASE-2026-001`); `id` is the internal UUID. `status` is one of
`open`/`in_progress`/`closed`/`archived`.

### `videos`
One uploaded file per row. `storage_path` is a generated, sanitized path
(never the raw uploaded filename — prevents path traversal). `sha256` is
indexed for provenance/duplicate-detection. Metadata (`width`, `height`,
`fps`, `total_frames`, `duration_seconds`) is extracted by OpenCV at upload
time, never guessed from the filename.

### `analyses`
One pipeline run against a video. Stores the exact settings used
(`detection_confidence`, `iou_threshold`, `frame_interval`, `tracker_name`)
so results are reproducible/explainable, plus `detector_backend` (which
concrete detector actually ran: `yolo` or `motion_fallback`).

### `processing_jobs`
Background-job bookkeeping for one `Analysis`: `status`, `current_stage`
(one of the 11 pipeline stages), `progress_percent`, timestamps, error text.
A new job row could be added per retry; the API surfaces the latest one.

### `tracked_objects`
One tracked identity for the whole video (`TrackedObjectRecord`).
`track_number` is the per-analysis display number ("Person #1").
`trajectory` is a JSON list of `{frame, timestamp, x, y, width, height}`.

### `object_detections`
One row per raw per-frame detection (many rows per tracked object).
`track_id` is nullable because a detection might not have been matched to a
track (e.g. very first frame before a track exists) — such rows are still
stored for audit purposes.

### `faces`
One row per detected face instance at a point in time. `landmarks` (468x3
floats), `representation_3d`, and `geometric_features` are stored as JSON
— see `docs/architecture-decisions.md` #6 for why these are not further
normalized into child tables.

### `model_runs`
One row per trained classifier version (`FaceClassifier.train()` in
`app/ml/classifier.py`). Metrics are nullable and rendered as
"Not available" rather than a fabricated number when absent.

### `facial_comparisons`
One row per analyst-initiated face comparison. `reference_face_id` is
nullable (a comparison can be classifier-only, with no explicit reference
face). `classifier_prediction` is null (not a fake value) until a model has
actually been trained.

### `evidence_frames`
One row per saved evidence frame; `reason` is one of the triggers in
`app/models/evidence.py:EVIDENCE_TRIGGERS`. Both the original and an
annotated (bounding-box-drawn) copy are stored on disk under
`data/evidence/<analysis_id>/`.

### `timeline_events`
One row per chronological event; `event_type` is one of
`app/models/timeline.py:EVENT_TYPES`. Optional FKs link back to the
tracked object / face / evidence frame that produced the event, so the UI
can jump from a timeline entry to the underlying record.

### `reports`
One row per generated PDF. `version` increments per analysis so
regeneration doesn't overwrite history; `file_path`/`filename` point at the
actual file under `data/reports/`.

## Indexes

- `cases.case_number` (unique)
- `videos.sha256`
- `object_detections (analysis_id, frame_number)` — the API's hottest query
  path (fetching a frame's detections)
- `timeline_events (analysis_id, timestamp_seconds)` — chronological reads
