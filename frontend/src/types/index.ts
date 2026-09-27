export interface Case {
  id: string;
  case_number: string;
  title: string;
  description: string | null;
  status: string;
  notes: string | null;
  analyst_id: string | null;
  analyst_name: string | null;
  video_count: number;
  created_at: string;
  updated_at: string;
}

export interface Video {
  id: string;
  case_id: string;
  original_filename: string;
  file_format: string;
  file_size_bytes: number;
  sha256: string;
  width: number;
  height: number;
  fps: number;
  total_frames: number;
  duration_seconds: number;
  uploaded_at: string;
}

export interface Analysis {
  id: string;
  video_id: string;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  started_at: string | null;
  completed_at: string | null;
  detection_confidence: number;
  iou_threshold: number;
  frame_interval: number;
  tracker_name: string;
  detector_backend: string | null;
  error_message: string | null;
  settings_summary: string;
  created_at: string;
}

export interface ProcessingJob {
  id: string;
  analysis_id: string;
  status: string;
  current_stage: string | null;
  progress_percent: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface ObjectSummary {
  class_name: string;
  count: number;
  first_seen: string;
  last_seen: string;
}

export interface TrackedObject {
  id: string;
  track_number: number;
  display_label: string;
  class_name: string;
  first_timestamp: number;
  last_timestamp: number;
  duration_seconds: number;
  detection_count: number;
  average_confidence: number;
  min_confidence: number;
  max_confidence: number;
  trajectory: { frame: number; timestamp: number; x: number; y: number; width: number; height: number }[];
}

export interface Face {
  id: string;
  track_id: string | null;
  frame_number: number;
  timestamp: number;
  face_found: boolean;
  num_faces_in_frame: number;
  landmark_confidence: number | null;
  quality_flags: string[];
  bbox: { x: number; y: number; width: number; height: number } | null;
  geometric_features: {
    euclidean: Record<string, number>;
    geodesic: Record<string, number | null>;
    ratios: Record<string, number | null>;
  } | null;
  feature_set_version: string | null;
}

export interface EvidenceFrame {
  id: string;
  frame_number: number;
  timestamp: number;
  reason: string;
  object_types: string[];
  confidence_values: number[];
  original_frame_path: string;
  annotated_frame_path: string | null;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  timestamp_seconds: number;
  event_type: string;
  description: string;
  confidence: number | null;
}

export interface ModelRun {
  id: string;
  model_version: string;
  algorithm: string;
  best_params: Record<string, unknown>;
  cv_folds: number;
  accuracy: number | string;
  precision: number | string;
  recall: number | string;
  f1_score: number | string;
  training_samples: number;
  dataset_description: string;
  trained_at: string;
}

export interface Report {
  id: string;
  case_id: string;
  analysis_id: string;
  status: string;
  version: number;
  filename: string | null;
  error_message: string | null;
  created_at: string;
}

export interface DashboardData {
  total_cases: number;
  total_videos_processed: number;
  total_analyses: number;
  total_detected_objects: number;
  total_tracked_objects: number;
  total_detected_faces: number;
  total_evidence_frames: number;
  total_reports_generated: number;
  recent_cases: Case[];
  recent_analyses: Analysis[];
}
