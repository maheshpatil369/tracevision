"""Import every model module here so `Base.metadata` sees all tables when
`app.database.init_db.init_db()` or Alembic autogenerate runs."""
from app.models.user import User            # noqa: F401
from app.models.case import Case            # noqa: F401
from app.models.video import Video          # noqa: F401
from app.models.analysis import Analysis, ProcessingJob   # noqa: F401
from app.models.detection import ObjectDetection, TrackedObjectRecord  # noqa: F401
from app.models.face import Face, ModelRun, FacialComparison  # noqa: F401
from app.models.evidence import EvidenceFrame  # noqa: F401
from app.models.timeline import TimelineEvent  # noqa: F401
from app.models.report import Report  # noqa: F401
