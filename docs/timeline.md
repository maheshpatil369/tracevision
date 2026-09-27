# Event Timeline

`TimelineEvent` rows are created inline during the orchestrator's frame
loop (`app/services/analysis_orchestrator.py`), not as a separate
post-processing pass, so timestamps come directly from the same frame
being processed at that moment.

## Event types currently generated
- `object_entered` — first appearance of a tracked object (paired with its
  `first_appearance` evidence frame)
- `object_exited` — once tracking finalizes, using each track's last
  timestamp
- `high_confidence_detection` — any detection >= 0.9 confidence
- `face_detected` — any successful face detection, including its quality
  flags in the description

`event_type` values not yet generated but defined in the schema
(`app/models/timeline.py:EVENT_TYPES`): `object_interaction`,
`evidence_captured` (evidence creation could emit its own event distinct
from `object_entered`), `analysis_started`/`analysis_completed`. Adding
these is schema-compatible and tracked in
`docs/implementation-checklist.md`.

## Ordering and retrieval

`GET /api/timeline/by-analysis/{analysis_id}` always returns events sorted
by `timestamp_seconds` (enforced by the query's `ORDER BY`, backed by the
`ix_timeline_analysis_ts` index — not by insertion order, which could
otherwise be scrambled by the pipeline's per-detection-then-per-track
processing sequence).
