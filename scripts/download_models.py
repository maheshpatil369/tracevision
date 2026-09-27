#!/usr/bin/env python3
"""Downloads the model assets TRACEVISION needs but does not (and should not)
vendor in the repository:

  1. YOLOv8n weights (object detection) — ultralytics auto-downloads this on
     first use, but this script fetches it up-front so the first real
     analysis run isn't slowed down by a mid-request download.
  2. MediaPipe FaceLandmarker task bundle (468-point facial landmarks).

Requires network access. If a download fails (e.g. offline environment),
the app still runs: object detection falls back to the motion-based
detector (app/cv/detector.py) and facial analysis is skipped and reported
as unavailable — both are clearly labeled, never faked (spec section 68).
"""
from __future__ import annotations

import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

FACE_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)


def _download(url: str, dest: str) -> bool:
    if os.path.isfile(dest):
        print(f"[download_models] already present: {dest}")
        return True
    print(f"[download_models] downloading {url} -> {dest}")
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"[download_models] OK: {dest} ({os.path.getsize(dest)} bytes)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[download_models] FAILED: {exc}")
        if os.path.isfile(dest):
            os.remove(dest)
        return False


def main():
    from app.config.settings import get_settings
    settings = get_settings()
    model_dir = os.path.join(BACKEND_DIR, settings.MODEL_DIRECTORY.lstrip("./"))
    os.makedirs(model_dir, exist_ok=True)

    ok_face = _download(FACE_LANDMARKER_URL, os.path.join(model_dir, settings.FACE_MODEL_FILENAME))

    ok_yolo = True
    try:
        from ultralytics import YOLO
        weights_path = os.path.join(model_dir, settings.YOLO_MODEL)
        if not os.path.isfile(weights_path):
            print(f"[download_models] downloading YOLO weights: {settings.YOLO_MODEL}")
            model = YOLO(settings.YOLO_MODEL)  # ultralytics downloads to its cache on first use
            # Copy the cached weights into our models/ directory for a clean, portable project.
            cached_path = getattr(model, "ckpt_path", None) or settings.YOLO_MODEL
            if os.path.isfile(cached_path):
                import shutil
                shutil.copyfile(cached_path, weights_path)
            print(f"[download_models] OK: {weights_path}")
        else:
            print(f"[download_models] already present: {weights_path}")
    except ImportError:
        print("[download_models] ultralytics is not installed; object detection will use the "
              "motion-based fallback detector until `pip install ultralytics` succeeds.")
        ok_yolo = False
    except Exception as exc:  # noqa: BLE001
        print(f"[download_models] YOLO download failed: {exc}")
        ok_yolo = False

    print("\nSummary:")
    print(f"  face_landmarker.task : {'OK' if ok_face else 'MISSING (facial analysis will be skipped)'}")
    print(f"  YOLO weights         : {'OK' if ok_yolo else 'MISSING (motion-fallback detector will be used)'}")


if __name__ == "__main__":
    main()
