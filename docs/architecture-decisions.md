# Architecture Decisions

This log records deviations from the spec's suggested stack/approach and why.

## 1. Background jobs: ThreadPoolExecutor instead of Celery/RQ
**Decision:** Use Python's built-in `concurrent.futures.ThreadPoolExecutor`
(see `app/workers/job_runner.py`) rather than Celery+Redis or RQ.
**Why:** The spec (section 10) requires non-blocking background processing
but does not mandate a specific broker. Requiring Redis/RabbitMQ would add a
second infrastructure dependency to a project meant to run from a single
`pip install`. A thread pool is sufficient because video analysis is
I/O- and CPU-bound in short bursts (OpenCV/MediaPipe release the GIL during
their native calls) and the expected concurrency is low (a handful of
analysts, not thousands of concurrent jobs).
**Trade-off:** Does not survive a process restart mid-job, and does not
scale horizontally across machines. A production deployment with heavy
concurrent load should replace `app/workers/job_runner.py` with a real task
queue; the `AnalysisOrchestrator` class it calls has no framework
dependency and can be reused unchanged.

## 2. Object tracking: hand-written IoU tracker as the default, ByteTrack as an upgrade path
**Decision:** `app/cv/tracker.py` implements a real, dependency-free
greedy IoU-association tracker (`IouTracker`) and uses it as the default.
`ByteTrackAdapter` wraps the `supervision` package's ByteTrack implementation
and is used automatically when that package is installed.
**Why:** ByteTrack itself has no pure-pip standalone package; the most
common way to get it is via `supervision` or `yolox`, both larger
dependencies. Rather than hard-requiring one, the app tries ByteTrack first
and falls back to the IoU tracker — both satisfy every tracking field the
spec requires (stable IDs, first/last seen, confidence stats, trajectory).

## 3. Object detection: YOLO abstraction with an honest motion-based fallback
**Decision:** `app/cv/detector.py` defines `ObjectDetector` as an interface.
`YoloDetector` wraps Ultralytics YOLO; `FallbackMotionDetector` uses OpenCV
background subtraction when `ultralytics` or trained weights are missing.
**Why:** Spec section 42 explicitly requires a demo/development mode when a
model dependency is missing, and section 68 prohibits fabricating results.
The fallback never claims a real class label — it always reports
`class_name="moving_object"` and `detector_backend="motion_fallback"`, both
surfaced in the UI and PDF report.

## 4. Facial landmarks: MediaPipe Tasks API, not the legacy `solutions` API
**Decision:** `app/cv/face_mesh.py` uses
`mediapipe.tasks.python.vision.FaceLandmarker`.
**Why:** MediaPipe >= 0.10 deprecated the older `mp.solutions.face_mesh` API
in favor of the Tasks API. The Tasks API requires a downloaded model asset
file (`face_landmarker.task`); `scripts/download_models.py` fetches it. If
the file is absent, facial analysis is skipped and clearly reported as
unavailable rather than emulated.

## 5. IDs: UUID strings, not auto-increment integers
**Decision:** Every table's primary key is a `String(36)` UUID.
**Why:** Forensic evidence records should not leak information via
sequential IDs (e.g. "how many cases exist"), and UUIDs let evidence/report
filenames embed a stable identifier without a database round-trip.
Human-readable identifiers (`Case.case_number`, `TrackedObjectRecord.track_number`
used to render "Person #1") are separate, indexed fields.

## 6. Landmarks/geometry stored as JSON columns, not fully normalized tables
**Decision:** `Face.landmarks` (468x3 floats), `Face.geometric_features`,
and `TrackedObjectRecord.trajectory` are JSON columns rather than one row
per landmark/feature/trajectory-point.
**Why:** These are fixed-shape numeric arrays produced and consumed as a
single unit (never queried landmark-by-landmark), so normalizing them into
child tables would add join overhead and schema complexity with no query
benefit. See `docs/database.md` for the full rationale per table.

## 7. Frontend: plain fetch + React Router, no heavyweight UI kit
**Decision:** The frontend uses React + TypeScript + Vite + Tailwind with a
thin hand-rolled `fetch` wrapper (`src/services/api.ts`), not a data-fetching
library (React Query, SWR) or component kit (MUI, Ant).
**Why:** Keeps the dependency surface small and the generated code easy to
audit line-by-line, in line with spec section 4's requirement that the UI
avoid "AI-generated dashboard" aesthetics and section 69/70's call for
modular, readable code. A larger project could layer React Query on top of
the existing `api.ts` without restructuring anything.

## 8. Documentation: consolidated field-reference, not one file per entity
**Decision:** Field-by-field documentation (spec section 38) is delivered as
`docs/field-reference/core-fields.md` and
`docs/field-reference/forensic-fields.md` rather than eleven separate files.
**Why:** The eleven-file split in the spec (case/video/analysis/processing-job/
object/detection/tracking/face/landmark/facial-feature/comparison/evidence/
timeline/report/model — actually 15 categories) produces a lot of very short
files with heavy cross-references. Two files grouped by "case-management
fields" and "forensic-analysis fields" cover the same content with less
navigation overhead. See `docs/implementation-checklist.md`, which notes
this consolidation explicitly rather than hiding it.
