"""TRACEVISION FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (analyses, cases, dashboard, forensic_data, health,
                             models, reports, videos)
from app.config.settings import get_settings
from app.database.init_db import init_db
from app.utils.errors import AppError

settings = get_settings()

logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG,
                     format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("tracevision")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered forensic video analysis: object detection & tracking, "
                "468-point facial landmark analysis, ML classification, and automated "
                "forensic PDF reporting. See /docs for the full API reference.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code,
                         content={"success": False, "error": {"code": exc.code, "message": exc.message}})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak a raw stack trace to the client (spec section 33/71); log it
    # server-side instead.
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={
        "success": False,
        "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please check server logs."},
    })


@app.on_event("startup")
def on_startup():
    import os
    for d in (settings.UPLOAD_DIRECTORY, settings.PROCESSED_DIRECTORY,
              settings.EVIDENCE_DIRECTORY, settings.REPORTS_DIRECTORY, settings.MODEL_DIRECTORY):
        os.makedirs(d, exist_ok=True)
    init_db()  # convenience for local/dev use; production should use `alembic upgrade head`.
    logger.info("%s v%s started.", settings.APP_NAME, settings.APP_VERSION)


app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(cases.router)
app.include_router(videos.router)
app.include_router(analyses.router)
app.include_router(forensic_data.router)
app.include_router(reports.router)
app.include_router(models.router)

# Serve evidence frame images so the frontend's <img> tags can load them directly.
import os
os.makedirs(settings.EVIDENCE_DIRECTORY, exist_ok=True)
app.mount("/media/evidence", StaticFiles(directory=settings.EVIDENCE_DIRECTORY), name="evidence")


@app.get("/")
def root():
    return {"success": True, "data": {"app": settings.APP_NAME, "version": settings.APP_VERSION,
                                       "docs": "/docs", "health": "/api/health"}}
