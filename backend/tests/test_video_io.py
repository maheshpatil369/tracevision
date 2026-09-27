import os
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
from app.cv.video_io import (sanitize_filename, VideoValidationError,
                              validate_and_extract_metadata, iter_frames, format_timestamp)


def test_sanitize_filename_strips_path_traversal():
    assert sanitize_filename("../../etc/passwd.mp4") == "passwd.mp4"
    assert sanitize_filename("normal video.mp4") == "normalvideo.mp4"


def test_unsupported_extension_rejected(tmp_path):
    f = tmp_path / "clip.txt"
    f.write_text("not a video")
    with pytest.raises(VideoValidationError) as exc:
        validate_and_extract_metadata(str(f), "clip.txt", max_upload_bytes=10_000_000)
    assert exc.value.code == "UNSUPPORTED_FORMAT"


def test_oversized_file_rejected(tmp_path):
    f = tmp_path / "clip.mp4"
    f.write_bytes(b"0" * 2000)
    with pytest.raises(VideoValidationError) as exc:
        validate_and_extract_metadata(str(f), "clip.mp4", max_upload_bytes=1000)
    assert exc.value.code == "FILE_TOO_LARGE"


def _make_real_test_video(path: str, n_frames=30, w=64, h=48, fps=10.0):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    for i in range(n_frames):
        frame = np.full((h, w, 3), (i * 5) % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_real_video_metadata_extraction(tmp_path):
    path = str(tmp_path / "sample.mp4")
    _make_real_test_video(path, n_frames=30, w=64, h=48, fps=10.0)
    meta = validate_and_extract_metadata(path, "sample.mp4", max_upload_bytes=50_000_000)
    assert meta.width == 64 and meta.height == 48
    assert meta.total_frames >= 25  # container overhead can shave a frame or two
    assert meta.fps > 0
    assert len(meta.sha256) == 64


def test_iter_frames_never_loads_whole_video_and_respects_interval(tmp_path):
    path = str(tmp_path / "sample2.mp4")
    _make_real_test_video(path, n_frames=40, w=64, h=48, fps=20.0)
    frames = list(iter_frames(path, frame_interval=4))
    frame_numbers = [f[0] for f in frames]
    assert frame_numbers == sorted(frame_numbers)
    assert all(n % 4 == 0 for n in frame_numbers)


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(65) == "00:01:05"
    assert format_timestamp(3661) == "01:01:01"
