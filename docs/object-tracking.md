# Object Tracking

`app/cv/tracker.py` defines the `Tracker` interface. `build_default_tracker()`
prefers `ByteTrackAdapter` (via the `supervision` package) and falls back to
the built-in `IouTracker` if `supervision` isn't installed.

## IouTracker (built-in default)
Greedy IoU-association: each frame, every existing track is matched to the
detection with the highest IoU overlap (same class, above `iou_threshold`,
default 0.3). Unmatched tracks accumulate a "missed frame" counter and are
only closed after `max_age` (default 15) consecutive misses — this is what
lets a track survive brief occlusion instead of spawning a new ID every time
an object is briefly hidden.

## What's stored per track (`TrackedObjectRecord`)
`track_number` (display ID, e.g. "Person #1"), `class_name`, `first_frame`/
`last_frame`, `first_timestamp`/`last_timestamp`, `detection_count`,
`average_confidence`/`min_confidence`/`max_confidence`, and the full
`trajectory` (list of per-frame bounding boxes) — every field spec section
13 requires.

## Object summary

`AnalysisService.get_objects_summary()` aggregates `object_detections` by
class into exactly the table spec section 14 describes: class, count, first
seen, last seen — computed live from stored detections, never hardcoded.
