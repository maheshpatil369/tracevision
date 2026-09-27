# Security

## Implemented

- **Upload validation** (`app/cv/video_io.py`): extension allow-list,
  file-size limit (`MAX_UPLOAD_SIZE`), and actual decodability check via
  OpenCV — the filename extension alone is never trusted.
- **Filename sanitization**: `sanitize_filename()` strips directory
  components and any character outside `[A-Za-z0-9._-]`, preventing path
  traversal (`../../etc/passwd.mp4` -> `passwd.mp4`).
- **Generated storage paths**: uploaded files are written to
  `<uuid>_<sanitized_name>`, never the raw client-supplied path.
- **No arbitrary file execution**: uploaded files are only ever opened by
  OpenCV as a video stream; nothing in the codebase `exec`s, `eval`s, or
  shells out with user-controlled input.
- **Parameterized queries**: all database access goes through SQLAlchemy's
  ORM/Core query builder — no raw string-formatted SQL anywhere.
- **Consistent error format**: `app/utils/errors.py` + `main.py`'s global
  exception handler ensure a raw Python traceback is never sent to the
  client; it is logged server-side instead (spec section 33/71).
- **Secrets via environment**: `SECRET_KEY` and `DATABASE_URL` come from
  `.env` (see `.env.example`), never hardcoded, and `.env` is git-ignored.
- **CORS allow-list**: `CORS_ORIGINS` explicitly enumerates allowed
  frontend origins rather than `allow_origins=["*"]`.

## Scaffolded but not wired into request auth

`app/models/user.py` and `requirements.txt` (`python-jose`, `passlib
[bcrypt]`) provide the pieces for real authentication (password hashing,
JWT), and `scripts/seed.py` creates a `demo_analyst` user — but **no API
route currently requires a valid token**; every endpoint is open. This is
explicitly called out here and in `docs/limitations.md` rather than
silently left out. Adding auth means: (1) a login endpoint issuing a JWT
via `python-jose`, (2) a `get_current_user` FastAPI dependency, (3)
applying it to the routers in `app/main.py`.

## Not implemented (explicitly out of scope for this build)

- Rate limiting / request throttling
- Audit logging of who accessed which case
- Role-based authorization (the `role` column exists on `User` but nothing
  reads it yet)
- Encryption at rest for uploaded video/evidence files (relies on the host
  filesystem's own security)
