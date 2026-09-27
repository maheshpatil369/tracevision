# Facial Analysis

For every detection whose class is `person`, the orchestrator crops the
bounding box and runs it through `app/cv/face_mesh.py`'s `FaceLandmarker`
(MediaPipe FaceLandmarker Tasks API). See `docs/facial-landmarks.md`,
`docs/facial-3d.md`, and `docs/geometric-features.md` for what happens once
a face is found.

## Honest handling of imperfect input (spec section 17)

| Situation | Behavior |
|---|---|
| No face in the crop | `face_found=False`, flag `no_face_detected`; nothing is stored as a fabricated face |
| Multiple faces in frame | Largest (by bbox area) is treated as the primary subject; flag `multiple_faces` |
| Partial/cropped face | Heuristic confidence < 0.85 -> flag `partial_face_or_cropped` |
| Low detection confidence | Face is not returned at all (gated by `min_detection_confidence`, default 0.5) |
| Model asset missing | `ModelAssetMissingError` raised at startup of that analysis; facial analysis is skipped for the whole run, reported as unavailable — never faked |

All flags are stored on the `Face` row (`quality_flags`) and shown next to
the face in the UI and in the PDF report, so an analyst never sees a
confident-looking result that was actually low quality.
