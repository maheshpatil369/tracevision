# Field Reference: Case Management

Covers Case, Video, Analysis, and Processing Job fields. Each entry:
name / label / type / required / default / source (user-entered vs
system-generated) / where it appears.

## Case (`app/models/case.py`, table `cases`)
| Field | Label | Type | Required | Source | Notes |
|---|---|---|---|---|---|
| `id` | Internal ID | UUID string | yes (auto) | system-generated | Primary key |
| `case_number` | Case Number | string(50) | yes | user-entered | Unique; `^[A-Za-z0-9._-]{3,50}$` |
| `title` | Title | string(200) | yes | user-entered | |
| `description` | Description | text | no | user-entered | |
| `status` | Status | enum | yes | system (default `open`) / user (via PATCH) | `open`/`in_progress`/`closed`/`archived` |
| `notes` | Notes | text | no | user-entered | |
| `analyst_id` | Analyst | UUID string (FK users.id) | no | user-entered | |
| `created_at`/`updated_at` | Created/Updated | datetime | yes | system-generated | |

API: `POST/GET/PATCH/DELETE /api/cases`. UI: Cases list + Case Detail page.

## Video (`app/models/video.py`, table `videos`)
| Field | Label | Type | Required | Source | Notes |
|---|---|---|---|---|---|
| `id` | Internal ID | UUID | yes | system | |
| `case_id` | Case | UUID (FK) | yes | system | Set from upload URL param |
| `original_filename` | Filename | string(255) | yes | user-entered (sanitized) | Display only, never used as a disk path |
| `storage_path` | Storage Path | string(500) | yes | system-generated | `<uuid>_<sanitized_name>` |
| `file_format` | Format | string(10) | yes | system (extracted) | mp4/avi/mov/mkv/webm |
| `file_size_bytes` | Size | integer | yes | system (extracted) | |
| `sha256` | SHA-256 | string(64) | yes | system (computed) | Provenance/dedup |
| `width`/`height` | Resolution | integer | yes | system (extracted via OpenCV) | |
| `fps` | Frame Rate | float | yes | system (extracted) | Falls back to 25.0 if container misreports 0 |
| `total_frames` | Total Frames | integer | yes | system (extracted) | |
| `duration_seconds` | Duration | float | yes | system (computed: frames/fps) | |

API: `POST /api/videos/upload`, `GET /api/videos/{id}`,
`GET /api/videos/by-case/{case_id}`, `DELETE /api/videos/{id}`.

## Analysis (`app/models/analysis.py`, table `analyses`)
| Field | Label | Type | Required | Source | Notes |
|---|---|---|---|---|---|
| `id` | Internal ID | UUID | yes | system | |
| `video_id` | Video | UUID (FK) | yes | system | |
| `status` | Status | enum | yes | system | `queued`/`processing`/`completed`/`failed`/`cancelled` |
| `started_at`/`completed_at` | Timestamps | datetime | no | system | |
| `detection_confidence` | Detection Confidence | float | yes | user (or default 0.4) | |
| `iou_threshold` | IoU Threshold | float | yes | user (or default 0.5) | |
| `frame_interval` | Frame Interval | integer | yes | user (or default 5) | |
| `tracker_name` | Tracker | string(30) | yes | user (`auto`/`iou`/`bytetrack`) | Resolved to actual tracker used post-run |
| `detector_backend` | Detector Backend | string(30) | no | system (set during run) | `yolo` or `motion_fallback` |
| `error_message` | Error | text | no | system | Populated only on failure |

API: `POST /api/analyses`, `GET /api/analyses/{id}`,
`GET /api/analyses/{id}/status`, `GET /api/analyses/by-video/{video_id}`,
`POST /api/analyses/{id}/cancel`.

## Processing Job (`app/models/analysis.py`, table `processing_jobs`)
| Field | Label | Type | Required | Source | Notes |
|---|---|---|---|---|---|
| `analysis_id` | Analysis | UUID (FK) | yes | system | |
| `status` | Status | enum | yes | system | mirrors Analysis status |
| `current_stage` | Stage | string(40) | no | system | one of `PROCESSING_STAGES` |
| `progress_percent` | Progress | integer 0-100 | yes | system (computed from stage index) | Never fake/animated |
| `error_message` | Error | text | no | system | |

API: nested in `GET /api/analyses/{id}/status`.
