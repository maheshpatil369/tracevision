#!/usr/bin/env python3
"""One-shot local setup: creates data directories, initializes the database
(via Alembic if available, else directly from the ORM metadata), and prints
next steps. Run from the project root:

    python scripts/setup.py
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)


def main():
    from app.config.settings import get_settings
    settings = get_settings()

    for rel_dir in (settings.UPLOAD_DIRECTORY, settings.PROCESSED_DIRECTORY,
                     settings.EVIDENCE_DIRECTORY, settings.REPORTS_DIRECTORY, settings.MODEL_DIRECTORY):
        abs_dir = os.path.join(BACKEND_DIR, rel_dir) if not os.path.isabs(rel_dir) else rel_dir
        os.makedirs(abs_dir, exist_ok=True)
        print(f"[setup] ensured directory: {abs_dir}")

    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=BACKEND_DIR)
        print("[setup] database migrated via alembic upgrade head")
    except Exception as exc:  # noqa: BLE001
        print(f"[setup] alembic not available/failed ({exc}); falling back to direct table creation")
        os.chdir(BACKEND_DIR)
        from app.database.init_db import init_db
        init_db()
        print("[setup] database initialized from ORM metadata")

    print("\nSetup complete. Next steps:")
    print("  1. python scripts/download_models.py   # downloads YOLO + face landmark models")
    print("  2. python scripts/health_check.py       # verify everything is working")
    print("  3. cd backend && uvicorn app.main:app --reload   # start the API")


if __name__ == "__main__":
    main()
