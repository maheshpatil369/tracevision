from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.session import get_db
from app.services.video_service import VideoService
from app.utils.errors import AppError

router = APIRouter(prefix="/api/videos", tags=["videos"])
settings = get_settings()


@router.post("/upload")
async def upload_video(case_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.size is not None and file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail={
            "code": "FILE_TOO_LARGE", "message": f"File exceeds the {settings.MAX_UPLOAD_SIZE} byte limit."})
    try:
        video = VideoService(db).upload_video(case_id, file.filename, file.file)
        return {"success": True, "data": video.to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.get("/{video_id}")
def get_video(video_id: str, db: Session = Depends(get_db)):
    try:
        return {"success": True, "data": VideoService(db).get_video(video_id).to_dict()}
    except AppError as e:
        raise e.to_http_exception()


@router.get("/by-case/{case_id}")
def list_videos_for_case(case_id: str, db: Session = Depends(get_db)):
    try:
        videos = VideoService(db).list_videos_for_case(case_id)
        return {"success": True, "data": [v.to_dict() for v in videos]}
    except AppError as e:
        raise e.to_http_exception()


@router.delete("/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db)):
    try:
        VideoService(db).delete_video(video_id)
        return {"success": True, "data": {"message": "Video deleted."}}
    except AppError as e:
        raise e.to_http_exception()
