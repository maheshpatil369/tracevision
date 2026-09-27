# Troubleshooting

## `python scripts/health_check.py` reports missing packages
Run `pip install -r backend/requirements.txt` inside your activated virtual
environment. If `mediapipe` or `opencv-python-headless` fail to build from
source, ensure you're on a supported Python version (3.11/3.12) and a
64-bit interpreter — both ship prebuilt wheels for common platforms.

## Facial analysis is always skipped / `face_landmarker` reports MISSING
`python scripts/download_models.py` needs outbound network access to fetch
`face_landmarker.task` from Google's model storage. If you're behind a
firewall/proxy, download it manually from the MediaPipe model zoo and place
it at `backend/models/face_landmarker.task`. Until it's present, this is
expected, honest behavior — not a bug — per spec section 68 (no fabricated
landmarks).

## Object detection always reports `detector_backend: "motion_fallback"`
Either `ultralytics` isn't installed, or `backend/models/yolov8n.pt` isn't
present. Run `python scripts/download_models.py`, or `pip install
ultralytics` and let it auto-download the weights on first use. The
fallback still runs and returns real (if generic) motion-region detections
— it is not an error state, just reduced capability.

## `alembic upgrade head` fails with "table already exists"
You likely ran the app once before Alembic was set up (it auto-creates
tables via `init_db()` as a convenience). Either delete
`backend/data/tracevision.db` and re-run `alembic upgrade head` on a clean
database, or `alembic stamp head` to mark the existing schema as current
without re-running the migration.

## Video upload fails with `UNREADABLE_VIDEO` / `NO_READABLE_FRAMES`
The file's extension is supported but OpenCV's installed FFmpeg backend
couldn't decode it — usually an unusual codec inside an `.mkv`/`.avi`
container. Re-encode with `ffmpeg -i input.mkv -c:v libx264 -c:a aac
output.mp4` and re-upload.

## Analysis stays `queued` and never starts processing
Check the backend process logs — the `ThreadPoolExecutor` in
`app/workers/job_runner.py` runs in-process, so if the API process was
restarted after a job was queued but before it ran, that job is lost (this
is a known limitation of the thread-pool approach; see
`docs/architecture-decisions.md` #1). Re-trigger via
`POST /api/analyses?video_id=...`.

## Frontend shows a blank page / network errors in the console
Confirm the backend is running on port 8000 and `frontend/vite.config.ts`'s
proxy target matches (or set `VITE_API_BASE_URL`). Check
`http://localhost:8000/api/health` directly in a browser first.

## `pip install` / `npm install` fail with network errors
This project's dependencies (FastAPI, SQLAlchemy, Ultralytics, React, Vite,
etc.) require outbound internet access to install from PyPI/npm. If you are
behind a restrictive proxy or an offline/air-gapped machine, configure your
package manager's proxy settings or use an internal mirror. See
`PROJECT_COMPLETION_REPORT.md` for exactly which parts of this project were
verified to run in a fully offline environment during development (the
CV/ML/reporting core) versus which require normal internet access
(the API/DB/frontend layers and model downloads).
