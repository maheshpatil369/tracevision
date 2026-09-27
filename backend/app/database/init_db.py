"""Creates all tables directly from the ORM metadata. Used by
scripts/setup.py and scripts/health_check.py for a fast local bootstrap.
Production deployments should prefer `alembic upgrade head` (see
backend/alembic/) so schema history is tracked."""
from __future__ import annotations

from app.database.base import Base
from app.database.session import engine

# Import every model module so its tables register on Base.metadata before
# create_all() runs. This import list IS the single source of truth for
# "every table the app defines" — see docs/database.md.
from app.models import (case, user, video, analysis, detection,  # noqa: F401
                         face, evidence, timeline, report)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized (tables created from ORM metadata).")
