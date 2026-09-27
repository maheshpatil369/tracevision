from __future__ import annotations

import os
import shutil
import uuid
from typing import BinaryIO, Optional

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.cv.video_io import VideoValidationError, sanitize_filename, validate_and_extract_metadata
from app.models.video import Video
from app.services.case_service import CaseService
from app.utils.errors import NotFoundError, ValidationAppError

settings = get_settings()


class VideoService:
    def __init__(self, db: Session):
        self.db = db
        self.case_service = CaseService(db)

    def upload_video(self, case_id: str, original_filename: str, file_obj: BinaryIO) -> Video:
        """Safely stores an uploaded video under a generated path (never the
        raw filename), then validates + extracts real metadata (spec section 8).
        Any failure removes the partially-written file rather than leaving
        orphaned data on disk."""
        case = self.case_service.get_case(case_id)  # raises NotFoundError if missing

        safe_name = sanitize_filename(original_filename)
        os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
        generated_name = f"{uuid.uuid4().hex}_{safe_name}"
        storage_path = os.path.join(settings.UPLOAD_DIRECTORY, generated_name)

        with open(storage_path, "wb") as out:
            shutil.copyfileobj(file_obj, out)

        try:
            metadata = validate_and_extract_metadata(
                storage_path, original_filename, max_upload_bytes=settings.MAX_UPLOAD_SIZE)
        except VideoValidationError as exc:
            if os.path.isfile(storage_path):
                os.remove(storage_path)
            raise ValidationAppError(exc.code, exc.message) from exc

        video = Video(
            case_id=case.id, original_filename=metadata.filename, storage_path=storage_path,
            file_format=metadata.file_format, file_size_bytes=metadata.file_size_bytes,
            sha256=metadata.sha256, width=metadata.width, height=metadata.height,
            fps=metadata.fps, total_frames=metadata.total_frames,
            duration_seconds=metadata.duration_seconds,
        )
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)
        return video

    def get_video(self, video_id: str) -> Video:
        video = self.db.get(Video, video_id)
        if not video:
            raise NotFoundError("Video", video_id)
        return video

    def list_videos_for_case(self, case_id: str) -> list[Video]:
        self.case_service.get_case(case_id)  # raises NotFoundError if missing
        from sqlalchemy import select
        rows = self.db.execute(select(Video).where(Video.case_id == case_id)
                                .order_by(Video.created_at.desc())).scalars().all()
        return list(rows)

    def delete_video(self, video_id: str) -> None:
        video = self.get_video(video_id)
        if os.path.isfile(video.storage_path):
            os.remove(video.storage_path)
        self.db.delete(video)
        self.db.commit()
