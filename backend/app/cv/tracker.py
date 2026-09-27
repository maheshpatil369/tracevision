"""
Multi-object tracking (spec section 13).

`IouTracker` is a real, dependency-free implementation of the same core idea
ByteTrack/BoT-SORT use for the "high-confidence" association stage: greedy
IoU matching between existing tracks and new detections each frame, with a
short "grace period" (max_age) before a track is closed. It is deliberately
simple so it needs no extra network-installed packages, while still
satisfying every field the spec requires (stable IDs across frames, first/last
seen, detection counts, confidence stats, trajectory).

If `bytetrack`/`supervision` become available in the deployment environment,
`ByteTrackAdapter` wraps them behind the same `Tracker` interface — the
orchestrator code does not need to change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .detector import Detection


def _iou(a: Detection, b: Detection) -> float:
    ax0, ay0, ax1, ay1 = a.x, a.y, a.x + a.width, a.y + a.height
    bx0, by0, bx1, by1 = b.x, b.y, b.x + b.width, b.y + b.height
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, a.width) * max(0.0, a.height)
    area_b = max(0.0, b.width) * max(0.0, b.height)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


@dataclass
class TrackedObject:
    track_id: int
    class_name: str
    first_frame: int
    last_frame: int
    first_timestamp: float
    last_timestamp: float
    detection_count: int = 0
    confidences: List[float] = field(default_factory=list)
    trajectory: List[dict] = field(default_factory=list)  # [{frame, timestamp, x, y, width, height}]
    _last_detection: Optional[Detection] = field(default=None, repr=False)
    _missed_frames: int = 0

    @property
    def duration(self) -> float:
        return round(self.last_timestamp - self.first_timestamp, 3)

    @property
    def average_confidence(self) -> float:
        return round(sum(self.confidences) / len(self.confidences), 4) if self.confidences else 0.0

    @property
    def min_confidence(self) -> float:
        return round(min(self.confidences), 4) if self.confidences else 0.0

    @property
    def max_confidence(self) -> float:
        return round(max(self.confidences), 4) if self.confidences else 0.0

    def update(self, det: Detection):
        self.last_frame = det.frame_number
        self.last_timestamp = det.timestamp
        self.detection_count += 1
        self.confidences.append(det.confidence)
        self.trajectory.append({
            "frame": det.frame_number, "timestamp": round(det.timestamp, 3),
            "x": det.x, "y": det.y, "width": det.width, "height": det.height,
        })
        self._last_detection = det
        self._missed_frames = 0

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id, "class_name": self.class_name,
            "first_frame": self.first_frame, "last_frame": self.last_frame,
            "first_timestamp": round(self.first_timestamp, 3),
            "last_timestamp": round(self.last_timestamp, 3),
            "duration_seconds": self.duration, "detection_count": self.detection_count,
            "average_confidence": self.average_confidence,
            "min_confidence": self.min_confidence, "max_confidence": self.max_confidence,
            "trajectory": self.trajectory,
        }


class Tracker:
    def update(self, detections: List[Detection]) -> List[TrackedObject]:
        raise NotImplementedError

    def finalize(self) -> List[TrackedObject]:
        raise NotImplementedError


class IouTracker(Tracker):
    """Greedy IoU-association tracker with class-consistency and a grace
    period (max_age) so brief occlusion doesn't spawn a new ID."""

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 15):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self._active: Dict[int, TrackedObject] = {}
        self._closed: List[TrackedObject] = []
        self._next_id = 1

    def _match(self, detections: List[Detection]) -> Tuple[Dict[int, Detection], List[Detection]]:
        matches: Dict[int, Detection] = {}
        unmatched = list(detections)
        candidates = []
        for tid, track in self._active.items():
            if track._last_detection is None:
                continue
            for det in unmatched:
                if det.class_name != track.class_name:
                    continue
                score = _iou(track._last_detection, det)
                if score >= self.iou_threshold:
                    candidates.append((score, tid, det))
        candidates.sort(key=lambda c: c[0], reverse=True)
        used_tids, used_dets = set(), set()
        for score, tid, det in candidates:
            if tid in used_tids or id(det) in used_dets:
                continue
            matches[tid] = det
            used_tids.add(tid)
            used_dets.add(id(det))
        remaining = [d for d in unmatched if id(d) not in used_dets]
        return matches, remaining

    def update(self, detections: List[Detection]) -> List[TrackedObject]:
        matches, unmatched = self._match(detections)
        self._last_assignment: Dict[int, int] = {}

        for tid, det in matches.items():
            self._active[tid].update(det)
            self._last_assignment[id(det)] = tid

        matched_ids = set(matches.keys())
        for tid, track in list(self._active.items()):
            if tid not in matched_ids:
                track._missed_frames += 1
                if track._missed_frames > self.max_age:
                    self._closed.append(track)
                    del self._active[tid]

        for det in unmatched:
            track = TrackedObject(
                track_id=self._next_id, class_name=det.class_name,
                first_frame=det.frame_number, last_frame=det.frame_number,
                first_timestamp=det.timestamp, last_timestamp=det.timestamp,
            )
            track.update(det)
            self._active[track.track_id] = track
            self._last_assignment[id(det)] = track.track_id
            self._next_id += 1

        return list(self._active.values())

    def get_track_id_for(self, det: Detection) -> Optional[int]:
        """Returns the track_id this tracker just assigned to `det` during
        the most recent `update()` call (must be called with the same
        Detection object instance passed into that call)."""
        return getattr(self, "_last_assignment", {}).get(id(det))

    def finalize(self) -> List[TrackedObject]:
        all_tracks = self._closed + list(self._active.values())
        self._active = {}
        return sorted(all_tracks, key=lambda t: t.track_id)


class ByteTrackAdapter(Tracker):
    """Wraps the real ByteTrack implementation (via the `supervision` or
    `yolox` packages) when installed. Falls back to raising so the
    orchestrator can catch this and use IouTracker instead — it never
    silently produces fake track IDs."""

    def __init__(self, frame_rate: int = 25):
        try:
            import supervision as sv  # noqa: F401
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "The `supervision` package (ByteTrack) is not installed. "
                "Falling back to the built-in IoU tracker."
            ) from exc
        import supervision as sv
        self._sv = sv
        self._bt = sv.ByteTrack(frame_rate=frame_rate)
        self._tracks: Dict[int, TrackedObject] = {}

    def update(self, detections: List[Detection]) -> List[TrackedObject]:
        import numpy as np
        sv = self._sv
        if not detections:
            sv_dets = sv.Detections.empty()
        else:
            xyxy = np.array([[d.x, d.y, d.x + d.width, d.y + d.height] for d in detections])
            conf = np.array([d.confidence for d in detections])
            cls = np.array([d.class_id for d in detections])
            sv_dets = sv.Detections(xyxy=xyxy, confidence=conf, class_id=cls)
        tracked = self._bt.update_with_detections(sv_dets)
        results = []
        self._last_assignment = {}
        for i, tid in enumerate(tracked.tracker_id):
            det = detections[i] if i < len(detections) else None
            if det is None:
                continue
            if tid not in self._tracks:
                self._tracks[tid] = TrackedObject(
                    track_id=int(tid), class_name=det.class_name,
                    first_frame=det.frame_number, last_frame=det.frame_number,
                    first_timestamp=det.timestamp, last_timestamp=det.timestamp,
                )
            self._tracks[tid].update(det)
            self._last_assignment[id(det)] = int(tid)
            results.append(self._tracks[tid])
        return results

    def get_track_id_for(self, det: Detection) -> Optional[int]:
        return getattr(self, "_last_assignment", {}).get(id(det))

    def finalize(self) -> List[TrackedObject]:
        return sorted(self._tracks.values(), key=lambda t: t.track_id)


def build_default_tracker(prefer_bytetrack: bool = True, frame_rate: int = 25) -> Tracker:
    if prefer_bytetrack:
        try:
            return ByteTrackAdapter(frame_rate=frame_rate)
        except Exception:
            pass
    return IouTracker()
