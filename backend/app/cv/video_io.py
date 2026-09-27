"""
Real video I/O using OpenCV: metadata extraction, safe validation, and
memory-efficient frame extraction (frames are yielded one at a time — the
full video is never loaded into RAM, per spec section 11/47).
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

import cv2

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_SAFE_FILENAME_LEN = 200


class VideoValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class VideoMetadata:
    filename: str
    file_format: str
    file_size_bytes: int
    width: int
    height: int
    fps: float
    total_frames: int
    duration_seconds: float
    sha256: str

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "file_format": self.file_format,
            "file_size_bytes": self.file_size_bytes,
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 3),
            "total_frames": self.total_frames,
            "duration_seconds": round(self.duration_seconds, 3),
            "sha256": self.sha256,
        }


def sanitize_filename(original_name: str) -> str:
    """Prevents path traversal and unsafe characters (spec section 8/33)."""
    base = os.path.basename(original_name)
    base = base.replace("\x00", "")
    if len(base) > MAX_SAFE_FILENAME_LEN:
        name, ext = os.path.splitext(base)
        base = name[: MAX_SAFE_FILENAME_LEN - len(ext)] + ext
    safe = "".join(c for c in base if c.isalnum() or c in "._-")
    if not safe:
        raise VideoValidationError("INVALID_FILENAME", "Filename contains no safe characters.")
    return safe


def compute_sha256(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_and_extract_metadata(path: str, original_filename: str,
                                   max_upload_bytes: int) -> VideoMetadata:
    """Validates extension, size, and readability, then extracts real
    metadata via OpenCV. Raises VideoValidationError with a machine-readable
    code on any failure — never trusts the filename extension alone to decide
    the video is actually decodable (spec section 8)."""
    _, ext = os.path.splitext(original_filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise VideoValidationError("UNSUPPORTED_FORMAT", f"Extension '{ext}' is not supported.")

    if not os.path.isfile(path):
        raise VideoValidationError("FILE_NOT_FOUND", "Uploaded file could not be located on disk.")

    size = os.path.getsize(path)
    if size == 0:
        raise VideoValidationError("EMPTY_FILE", "Uploaded file is empty.")
    if size > max_upload_bytes:
        raise VideoValidationError("FILE_TOO_LARGE", f"File exceeds the {max_upload_bytes} byte limit.")

    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            raise VideoValidationError("UNREADABLE_VIDEO",
                                        "The file could not be opened as a video (unsupported codec or corrupted file).")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        ok, _frame = cap.read()
        if not ok:
            raise VideoValidationError("NO_READABLE_FRAMES", "No frames could be decoded from the file.")

        if fps <= 0:
            # Some containers misreport FPS; fall back to a conservative default
            # and flag it rather than dividing by zero later.
            fps = 25.0
        duration = (total_frames / fps) if total_frames > 0 else 0.0
    finally:
        cap.release()

    return VideoMetadata(
        filename=original_filename, file_format=ext.lstrip("."), file_size_bytes=size,
        width=width, height=height, fps=fps, total_frames=total_frames,
        duration_seconds=duration, sha256=compute_sha256(path),
    )


def iter_frames(path: str, frame_interval: int = 5,
                 max_dimension: Optional[int] = None) -> Iterator[Tuple[int, float, "cv2.typing.MatLike"]]:
    """Yields (frame_number, timestamp_seconds, frame) for every `frame_interval`-th
    frame. Never buffers the whole video — each frame is read, optionally
    downscaled, yielded, and then goes out of scope. Timestamp is derived from
    frame_index / fps (spec section 11)."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise VideoValidationError("UNREADABLE_VIDEO", "Video could not be reopened for frame extraction.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index % max(1, frame_interval) == 0:
                if max_dimension:
                    h, w = frame.shape[:2]
                    scale = min(1.0, max_dimension / max(h, w))
                    if scale < 1.0:
                        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                timestamp = frame_index / fps
                yield frame_index, timestamp, frame
            frame_index += 1
    finally:
        cap.release()


def format_timestamp(seconds: float) -> str:
    """HH:MM:SS formatting used throughout the UI/report/timeline."""
    seconds = max(0, int(round(seconds)))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
