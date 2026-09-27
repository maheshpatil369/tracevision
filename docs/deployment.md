# Deployment

## Native (single machine)
Follow `docs/installation.md`. Run the backend behind a process manager
(systemd, supervisor, or `pm2`) instead of `--reload`:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```
Build the frontend as static files and serve them from any static host or
reverse proxy (nginx, Caddy):
```bash
cd frontend && npm run build   # outputs frontend/dist
```
Point your reverse proxy's `/api` and `/media` locations at the backend
(port 8000) and everything else at `frontend/dist`.

## Docker
```bash
docker compose up --build
```
See `docker-compose.yml` / `Dockerfile`. The backend container runs
`alembic upgrade head` before starting uvicorn. Mount `backend/data` and
`backend/models` as volumes (already configured) so uploaded videos,
evidence, reports, and downloaded models persist across container
restarts.

## Database
SQLite (default) is fine for a single-analyst or small-team deployment.
For concurrent multi-analyst use, point `DATABASE_URL` at PostgreSQL:
```
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/tracevision
```
No code changes are needed — SQLAlchemy/Alembic both work against either
backend; the `connect_args={"check_same_thread": False}` in
`app/database/session.py` is a SQLite-only setting that's skipped
automatically for non-SQLite URLs.

## Scaling background jobs
The default `ThreadPoolExecutor` (see `docs/architecture-decisions.md` #1)
is appropriate for light concurrent load. For heavier throughput, replace
`app/workers/job_runner.py`'s `submit_analysis_job()` with a real task
queue (Celery + Redis, or RQ) calling the same
`AnalysisOrchestrator.run(analysis_id)` — that class has no FastAPI/thread
dependency and can be invoked from any worker process.

## GPU acceleration
Install a CUDA build of PyTorch before `ultralytics` (see
`docs/installation.md` #4). No environment variable is needed —
`ultralytics` and MediaPipe both auto-detect available GPUs.

## Environment checklist before going live
- [ ] Change `SECRET_KEY` from the default
- [ ] Set `DEBUG=false`
- [ ] Point `CORS_ORIGINS` at your real frontend domain(s) only
- [ ] Put the deployment behind HTTPS (a reverse proxy like nginx/Caddy)
- [ ] Decide on and implement authentication (see `docs/security.md`) —
      **not implemented by default in this build**
- [ ] Review `docs/privacy.md` for your jurisdiction's requirements
