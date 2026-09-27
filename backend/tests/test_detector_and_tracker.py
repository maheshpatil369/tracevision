import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
from app.cv.detector import Detection, FallbackMotionDetector, SUPPORTED_CLASSES_DOC
from app.cv.tracker import IouTracker


def test_fallback_detector_returns_no_detections_on_static_frames():
    det = FallbackMotionDetector()
    frame = np.full((240, 320, 3), 50, dtype=np.uint8)
    # Feed several identical frames: no motion, so no detections should ever
    # be fabricated once the background model warms up.
    results = []
    for i in range(10):
        results.append(det.detect(frame, frame_number=i, timestamp=i / 25.0))
    assert all(r == [] for r in results[5:])


def test_fallback_detector_flags_backend_honestly():
    det = FallbackMotionDetector()
    frame1 = np.full((240, 320, 3), 30, dtype=np.uint8)
    frame2 = frame1.copy()
    frame2[50:150, 50:150] = 220  # inject a moving bright block
    dets = []
    for i in range(8):
        f = frame2 if i == 7 else frame1
        dets = det.detect(f, frame_number=i, timestamp=i / 25.0)
    for d in dets:
        assert d.detector_backend == "motion_fallback"
        assert d.class_name == "moving_object"  # never claims a real class label


def test_supported_classes_doc_is_non_empty():
    assert "person" in SUPPORTED_CLASSES_DOC


def _det(frame_number, x, y, cls="person", conf=0.9):
    return Detection(frame_number=frame_number, timestamp=frame_number / 25.0,
                      class_id=0, class_name=cls, confidence=conf,
                      x=x, y=y, width=40, height=80, detector_backend="test")


def test_tracker_maintains_stable_id_across_frames():
    tracker = IouTracker(iou_threshold=0.3, max_age=5)
    for frame in range(10):
        # object moves slightly to the right each frame
        tracker.update([_det(frame, x=10 + frame * 2, y=10)])
    tracks = tracker.finalize()
    assert len(tracks) == 1
    t = tracks[0]
    assert t.detection_count == 10
    assert t.first_frame == 0 and t.last_frame == 9


def test_tracker_creates_separate_ids_for_unrelated_objects():
    tracker = IouTracker()
    tracker.update([_det(0, x=10, y=10), _det(0, x=500, y=400)])
    tracker.update([_det(1, x=12, y=10), _det(1, x=505, y=400)])
    tracks = tracker.finalize()
    assert len(tracks) == 2


def test_tracker_closes_track_after_max_age_missed_frames():
    tracker = IouTracker(max_age=2)
    tracker.update([_det(0, x=10, y=10)])
    for f in range(1, 6):
        tracker.update([])  # object disappears
    tracks = tracker.finalize()
    assert len(tracks) == 1
    assert tracks[0].last_frame == 0
