"""
Background job execution (spec section 10). Uses a simple in-process
ThreadPoolExecutor rather than Celery/RQ — this avoids requiring Redis/a
broker for a project that must "just work" after `pip install`, while still
keeping the FastAPI request/response cycle non-blocking for long-running
video analysis.

Each submitted job gets its OWN database session (SQLAlchemy sessions are
not thread-safe to share), created via `session_scope()`.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from app.database.session import session_scope
from app.services.analysis_orchestrator import AnalysisOrchestrator

logger = logging.getLogger("tracevision.worker")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tracevision-analysis")
_futures: Dict[str, object] = {}


def _run_job(analysis_id: str):
    logger.info("Starting analysis job for analysis_id=%s", analysis_id)
    try:
        with session_scope() as db:
            orchestrator = AnalysisOrchestrator(db)
            orchestrator.run(analysis_id)
        logger.info("Analysis job completed for analysis_id=%s", analysis_id)
    except Exception:
        logger.exception("Analysis job failed for analysis_id=%s", analysis_id)


def submit_analysis_job(analysis_id: str) -> None:
    """Queues the analysis for background processing and returns immediately
    (spec section 10: do not block the request while processing)."""
    future = _executor.submit(_run_job, analysis_id)
    _futures[analysis_id] = future


def is_job_running(analysis_id: str) -> bool:
    future = _futures.get(analysis_id)
    return bool(future and not future.done())
