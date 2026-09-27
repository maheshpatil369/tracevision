"""Central application configuration, loaded from environment variables
(spec section 34). Every setting has a safe local default so a fresh clone
works out of the box, but nothing here hardcodes a machine-specific path —
all paths are relative to the project root or overridable via .env."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "TRACEVISION"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./data/tracevision.db"

    UPLOAD_DIRECTORY: str = "./data/uploads"
    PROCESSED_DIRECTORY: str = "./data/processed"
    EVIDENCE_DIRECTORY: str = "./data/evidence"
    REPORTS_DIRECTORY: str = "./data/reports"
    MODEL_DIRECTORY: str = "./models"

    YOLO_MODEL: str = "yolov8n.pt"
    FACE_MODEL_FILENAME: str = "face_landmarker.task"

    DETECTION_CONFIDENCE: float = 0.4
    DETECTION_IOU_THRESHOLD: float = 0.5
    FRAME_INTERVAL: int = 5
    MAX_PROCESSING_DIMENSION: int = 960
    TRACKER_MAX_AGE: int = 15
    TRACKER_IOU_THRESHOLD: float = 0.3
    FACE_MIN_DETECTION_CONFIDENCE: float = 0.5

    MAX_UPLOAD_SIZE: int = 2 * 1024 * 1024 * 1024  # 2 GB

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    SECRET_KEY: str = "change-me-in-production-please"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
