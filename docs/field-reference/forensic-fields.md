# Field Reference: Forensic Analysis Data

Covers Object Detection, Tracked Object, Face, Facial Comparison, Model Run,
Evidence Frame, Timeline Event, and Report fields.

## Object Detection (`app/models/detection.py`, table `object_detections`)
| Field | Label | Type | Source | Notes |
|---|---|---|---|---|
| `analysis_id` | Analysis | UUID (FK) | system | |
| `track_id` | Track | UUID (FK, nullable) | system | Set after tracker finalizes |
| `frame_number` | Frame # | integer | system (from video decode) | |
| `timestamp_seconds` | Timestamp | float | system (frame/fps) | |
| `class_id`/`class_name` | Class | int / string(50) | system (model output) | `-1`/`"moving_object"` for the motion fallback |
| `confidence` | Confidence | float | system (model output) | Never fabricated |
| `bbox_x/y/width/height` | Bounding Box | float | system (model output) | Pixel coordinates |
| `detector_backend` | Backend | string(30) | system | `yolo` / `motion_fallback` |

API: `GET /api/objects/by-analysis/{id}` (aggregated summary).

## Tracked Object (`app/models/detection.py`, table `tracked_objects`)
| Field | Label | Type | Source | Notes |
|---|---|---|---|---|
| `track_number` | Display # | integer | system | Drives "Person #1" style labels |
| `class_name` | Class | string(50) | system | |
| `first_frame`/`last_frame` | Frame range | integer | system | |
| `first_timestamp`/`last_timestamp` | Time range | float | system | |
| `detection_count` | Detections | integer | system | |
| `average_confidence`/`min_confidence`/`max_confidence` | Confidence stats | float | system (computed) | |
| `trajectory` | Trajectory | JSON list | system | `[{frame,timestamp,x,y,width,height}, ...]` |

API: `GET /api/tracks/by-analysis/{id}`.

## Face (`app/models/face.py`, table `faces`)
| Field | Label | Type | Source | Notes |
|---|---|---|---|---|
| `analysis_id`/`track_id` | Links | UUID (FK) | system | `track_id` nullable |
| `frame_number`/`timestamp_seconds` | When | int/float | system | |
| `face_found` | Face Found | boolean | system | |
| `num_faces_in_frame` | Face Count | integer | system | Flags `multiple_faces` if > 1 |
| `landmark_confidence` | Confidence | float, nullable | system (heuristic) | Not the detector's own gating threshold — see docs/facial-analysis.md |
| `quality_flags` | Quality Flags | JSON list | system | e.g. `partial_face_or_cropped`, `multiple_faces` |
| `bbox` | Bounding Box | JSON, nullable | system | Normalized 0-1 |
| `landmarks` | 468 Landmarks | JSON (468x3), nullable | system (MediaPipe) | Omitted from list APIs unless `include_landmarks=true` |
| `landmark_model_version` | Model Version | string(50) | system | `"mediapipe-face_landmarker"` |
| `representation_3d` | 3D Representation | JSON, nullable | system (derived) | Centered/scale-normalized point cloud |
| `geometric_features` | Geometric Features | JSON, nullable | system (computed) | Euclidean/geodesic/ratios/vector |
| `feature_set_version` | Feature Version | string(30) | system | `"geom-v1"` |

API: `GET /api/faces/by-analysis/{id}`.

## Facial Comparison (`app/models/face.py`, table `facial_comparisons`)
| Field | Label | Type | Source | Notes |
|---|---|---|---|---|
| `face_id` | Subject Face | UUID (FK) | user (selects which face) | |
| `reference_face_id` | Reference Face | UUID (FK), nullable | user | |
| `reference_label` | Reference Label | string(150), nullable | user | For an external reference not itself a stored Face |
| `similarity_score` | Similarity | float, nullable | system (cosine similarity) | `null` if no reference supplied |
| `classifier_prediction` | Classifier Result | string(100), nullable | system | `null` until a model is trained — never guessed |
| `classifier_probabilities` | Probabilities | JSON, nullable | system | |
| `model_version_used` | Model Version | string(100), nullable | system | |
| `analyst_notes` | Notes | string(1000), nullable | user-entered | |

API: `POST /api/models/compare`.

## Model Run (`app/models/face.py`, table `model_runs`)
| Field | Label | Type | Source | Notes |
|---|---|---|---|---|
| `model_version` | Version | string(100), unique | system | `<algorithm>-<unix_timestamp>` |
| `algorithm` | Algorithm | string(50) | user (selects) | random_forest / svm / logistic_regression |
| `best_params` | Best Hyperparameters | JSON | system (GridSearchCV/RandomizedSearchCV) | |
| `cv_folds` | CV Folds | integer | system (adjusted for data size) | |
| `accuracy`/`precision`/`recall`/`f1_score` | Metrics | float, nullable | system (computed on held-out split) | `null` -> "Not available", never fabricated |
| `training_samples` | Sample Count | integer | system | |
| `dataset_description` | Dataset | string(255) | user-entered | |

API: `POST /api/models/train`, `GET /api/models`.

## Evidence Frame (`app/models/evidence.py`, table `evidence_frames`)
| Field | Label | Type | Source | Notes |
|---|---|---|---|---|
| `frame_number`/`timestamp_seconds` | When | int/float | system | |
| `reason` | Reason | string(40) | system | One of `EVIDENCE_TRIGGERS`; currently only `first_appearance` is generated (see docs/evidence.md) |
| `object_ids`/`object_types`/`confidence_values` | Involved Objects | JSON | system | |
| `original_frame_path` | Original Image | string(500) | system | |
| `annotated_frame_path` | Annotated Image | string(500), nullable | system | Bounding box + label overlay |

API: `GET /api/evidence/by-analysis/{id}`.

## Timeline Event (`app/models/timeline.py`, table `timeline_events`)
| Field | Label | Type | Source | Notes |
|---|---|---|---|---|
| `timestamp_seconds` | Timestamp | float | system | |
| `event_type` | Type | string(40) | system | One of `EVENT_TYPES` |
| `description` | Description | string(300) | system (templated) | |
| `confidence` | Confidence | float, nullable | system | |
| `related_track_id`/`related_face_id`/`evidence_frame_id` | Links | UUID (FK), nullable | system | For UI "jump to" navigation |

API: `GET /api/timeline/by-analysis/{id}` (always chronologically sorted).

## Report (`app/models/report.py`, table `reports`)
| Field | Label | Type | Source | Notes |
|---|---|---|---|---|
| `case_id`/`analysis_id` | Links | UUID (FK) | system | |
| `status` | Status | string(20) | system | `pending`/`generating`/`completed`/`failed` |
| `version` | Version | integer | system | Increments per analysis |
| `file_path`/`filename` | File | string, nullable | system | Set once generation succeeds |
| `error_message` | Error | string(500), nullable | system | |

API: `POST /api/reports`, `GET /api/reports/{id}`,
`GET /api/reports/{id}/download`, `GET /api/reports/by-case/{case_id}`.
