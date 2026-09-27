# Geometric Features

`app/cv/geometry.py`'s `FaceGeometryEngine` computes everything spec
section 20-21 requires, real and tested (see `backend/tests/test_geometry.py`,
27/27 tests passing during development — run against generated synthetic
landmark data, since no real face imagery ships with this repository).

## 1. Euclidean distances
Straight-line distance between 10 fixed named landmark pairs (bi-ocular
width, inter-canthal width, mouth width, nose-to-chin, face height, jaw
width, eye openings, mouth opening, inter-brow width).

## 2. Geodesic distances
Shortest-path distance across the **real** MediaPipe face-mesh tessellation
graph (2,556 edges, loaded from `mediapipe.tasks.python.vision.
FaceLandmarksConnections` — static topology data bundled with the package,
not something fetched at runtime), computed via `scipy.sparse.csgraph.
shortest_path` (Dijkstra). This is mathematically guaranteed to be >= the
Euclidean distance for the same pair (verified by
`test_geodesic_distances_are_greater_or_equal_to_euclidean`).

## 3. Landmark ratios
8 named ratios (e.g. `jaw_width_over_face_height`,
`mouth_opening_over_face_height`) computed from the Euclidean distances
above. A ratio is `None` (rendered "Not available") when its denominator is
missing or zero — never a divide-by-zero crash or a fabricated number.

## 4. Feature vector
All Euclidean + geodesic + ratio values, sorted by key name for a stable
order, concatenated into one vector (`Face.geometric_features["vector"]`)
plus its parallel `vector_names` list. `FEATURE_SET_VERSION` ("geom-v1") is
stored alongside so a future change to the feature definitions doesn't
silently produce vectors incomparable to older ones.

## Determinism

Given the same landmark array, `build_feature_vector()` always returns
the same vector — no randomness anywhere in the geometry pipeline
(`test_feature_vector_is_deterministic`). This is what makes stored feature
vectors safe to feed into classifier training later.
