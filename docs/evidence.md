# Evidence Frames

`AnalysisOrchestrator._save_evidence_frame()` writes both an original and an
annotated (bounding-box + label overlay) JPEG under
`data/evidence/<analysis_id>/` and creates an `EvidenceFrame` row.

## Trigger implemented in this build

- `first_appearance` — the first frame in which each tracked object was
  observed.

## Triggers defined but not yet wired up

`app/models/evidence.py:EVIDENCE_TRIGGERS` also defines `last_appearance`,
`high_confidence_detection`, `face_detected`, `important_event`, and
`analyst_selected` as valid values the schema supports, but the
orchestrator currently only calls `_save_evidence_frame()` for
`first_appearance` (to keep evidence storage bounded per spec section 15's
"do not save every frame unnecessarily"). Extending this to also save
`last_appearance` and `face_detected` frames is a straightforward addition
to `analysis_orchestrator.py` — see `docs/implementation-checklist.md` for
this being tracked as PARTIAL rather than COMPLETE.

## Retrieval

`GET /api/evidence/by-analysis/{analysis_id}` returns every evidence frame
for a run (timestamp, reason, object types/confidences, image paths). The
frontend's Evidence tab renders them as an image gallery with an explicit
"No evidence frames available." empty state.
