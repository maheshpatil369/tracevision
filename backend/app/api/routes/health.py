"""GET /health (spec section 45): reports API/database/storage/model status
so `scripts/health_check.py` (and the frontend) can tell a developer exactly
what's missing rather than a generic 500."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.session import get_db

router = APIRouter(prefix="/api/health", tags=["health"])
settings = get_settings()


@router.get("")
def health_check(db: Session = Depends(get_db)):
    checks = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        checks["database"] = {"status": "error", "detail": str(exc)}

    storage_dirs = {
        "upload_directory": settings.UPLOAD_DIRECTORY,
        "evidence_directory": settings.EVIDENCE_DIRECTORY,
        "reports_directory": settings.REPORTS_DIRECTORY,
    }
    checks["storage"] = {}
    for name, path in storage_dirs.items():
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, ".health_check_tmp")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            checks["storage"][name] = "writable"
        except Exception as exc:  # noqa: BLE001
            checks["storage"][name] = f"error: {exc}"

    yolo_path = os.path.join(settings.MODEL_DIRECTORY, settings.YOLO_MODEL)
    face_path = os.path.join(settings.MODEL_DIRECTORY, settings.FACE_MODEL_FILENAME)
    checks["models"] = {
        "yolo_weights": "present" if os.path.isfile(yolo_path) else
            "missing (motion-fallback detector will be used instead)",
        "face_landmarker": "present" if os.path.isfile(face_path) else
            "missing (facial analysis will be skipped until downloaded)",
    }

    try:
        import mediapipe  # noqa: F401
        checks["dependencies_mediapipe"] = "installed"
    except Exception:
        checks["dependencies_mediapipe"] = "NOT installed"
    try:
        import ultralytics  # noqa: F401
        checks["dependencies_ultralytics"] = "installed"
    except Exception:
        checks["dependencies_ultralytics"] = "NOT installed (motion-fallback detector will be used)"

    overall_ok = checks["database"]["status"] == "ok" and all(
        v == "writable" for v in checks["storage"].values())

    return {"success": True, "data": {"status": "ok" if overall_ok else "degraded", "checks": checks,
                                       "app_version": settings.APP_VERSION}}
