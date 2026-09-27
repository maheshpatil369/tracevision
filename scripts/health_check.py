#!/usr/bin/env python3
"""Standalone health check (spec section 45). Verifies the local environment
without needing the API server to already be running — useful right after
`python scripts/setup.py`, before starting uvicorn.

    python scripts/health_check.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, str(exc)
    status = "OK" if ok else "FAIL"
    print(f"[{status:4}] {name}: {detail}")
    return ok


def check_python_deps():
    missing = []
    for pkg in ("fastapi", "sqlalchemy", "uvicorn", "cv2", "mediapipe", "sklearn", "reportlab", "numpy"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        return False, f"missing packages: {', '.join(missing)} (pip install -r requirements.txt)"
    return True, "all required packages import successfully"


def check_optional_deps():
    optional_missing = []
    for pkg in ("ultralytics", "supervision"):
        try:
            __import__(pkg)
        except ImportError:
            optional_missing.append(pkg)
    if optional_missing:
        return True, (f"optional packages not installed: {', '.join(optional_missing)} "
                       "(app will use fallback detector/tracker)")
    return True, "all optional packages installed"


def check_database():
    from app.database.session import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True, "database connection OK"


def check_storage():
    from app.config.settings import get_settings
    settings = get_settings()
    for d in (settings.UPLOAD_DIRECTORY, settings.EVIDENCE_DIRECTORY, settings.REPORTS_DIRECTORY):
        os.makedirs(d, exist_ok=True)
        test_file = os.path.join(d, ".health_check_tmp")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
    return True, "upload/evidence/reports directories are writable"


def check_models():
    from app.config.settings import get_settings
    settings = get_settings()
    face_path = os.path.join(settings.MODEL_DIRECTORY, settings.FACE_MODEL_FILENAME)
    yolo_path = os.path.join(settings.MODEL_DIRECTORY, settings.YOLO_MODEL)
    msgs = []
    msgs.append(f"face_landmarker: {'present' if os.path.isfile(face_path) else 'MISSING (run scripts/download_models.py)'}")
    msgs.append(f"yolo weights: {'present' if os.path.isfile(yolo_path) else 'MISSING (motion-fallback detector will be used)'}")
    return True, "; ".join(msgs)


def main():
    results = [
        check("Required Python packages", check_python_deps),
        check("Optional Python packages", check_optional_deps),
        check("Database connectivity", check_database),
        check("Storage directories writable", check_storage),
        check("Model assets", check_models),
    ]
    print()
    if all(results):
        print("All checks passed (or degraded-but-functional). TRACEVISION is ready.")
        sys.exit(0)
    else:
        print("One or more checks failed. Resolve the FAIL items above before starting the API.")
        sys.exit(1)


if __name__ == "__main__":
    main()
