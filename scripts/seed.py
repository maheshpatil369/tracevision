#!/usr/bin/env python3
"""Seeds a development analyst account and a sample case (spec section 73).
Never inserts fake forensic evidence, detections, or reports — only case
management scaffolding a developer can then upload a real (or their own
test) video into.

    python scripts/seed.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)


def main():
    import hashlib
    from app.database.init_db import init_db
    from app.database.session import session_scope
    from app.models.case import Case
    from app.models.user import User

    init_db()

    with session_scope() as db:
        existing = db.query(User).filter_by(username="demo_analyst").first()
        if existing:
            print("[seed] demo_analyst already exists, skipping user creation")
            analyst = existing
        else:
            # Development-only credential. This is sample/demo data, not a
            # real account — change it (or delete this user) before any
            # real deployment. Hashing is a simple, dependency-free SHA-256
            # placeholder; production auth should use passlib/bcrypt
            # (already wired for that in requirements.txt).
            analyst = User(
                username="demo_analyst", full_name="Demo Analyst", email="demo@example.invalid",
                hashed_password=hashlib.sha256(b"change-me").hexdigest(), role="analyst",
            )
            db.add(analyst)
            db.flush()
            print(f"[seed] created demo_analyst (id={analyst.id})")

        existing_case = db.query(Case).filter_by(case_number="CASE-DEMO-001").first()
        if existing_case:
            print("[seed] sample case CASE-DEMO-001 already exists, skipping")
        else:
            case = Case(
                case_number="CASE-DEMO-001", title="Sample Development Case",
                description="Sample case created by scripts/seed.py for local development. "
                            "Upload your own test video to run a real analysis.",
                status="open", analyst_id=analyst.id,
                notes="This is development sample data, not a real forensic case.",
            )
            db.add(case)
            print("[seed] created sample case CASE-DEMO-001")

    print("[seed] done.")


if __name__ == "__main__":
    main()
