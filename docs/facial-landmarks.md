# 468 Facial Landmarks

`app/cv/face_mesh.py` uses MediaPipe's `FaceLandmarker` task
(`face_landmarker.task` model asset, downloaded by
`scripts/download_models.py`). The model outputs 478 points when iris
refinement is included; this project keeps exactly the first 468 indices
(the canonical FaceMesh tessellation space) so every downstream geometry
calculation has a stable, spec-compliant index space regardless of whether
iris points are present.

## Storage

`Face.landmarks` stores the full 468x3 array (x, y, z — MediaPipe's
normalized image-relative coordinates, z roughly depth-relative to the
face center) as JSON. `Face.landmark_model_version` records which model
produced them (`"mediapipe-face_landmarker"`), so results remain
attributable if the model is upgraded later.

## Visualization

The frontend's Faces tab (`frontend/src/pages/AnalysisDetail.tsx`) shows
per-face metadata and geometric features. Landmarks themselves are omitted
from the default API response (`include_landmarks=false`) because 468
points x 3 floats is a large payload for a list view; pass
`?include_landmarks=true` on `GET /api/faces/by-analysis/{id}` to fetch the
full coordinate set for a detailed inspection view.
