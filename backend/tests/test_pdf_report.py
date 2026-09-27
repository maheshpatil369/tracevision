import os
from app.reporting.pdf_report import generate_forensic_report, build_conclusion_text


def test_report_generates_real_pdf_with_empty_data(tmp_path):
    out = str(tmp_path / "report.pdf")
    data = {
        "case": {"case_id": "CASE-2026-001", "title": "Test Case", "analyst": "J. Analyst"},
        "video": {"filename": "sample.mp4", "duration_display": "00:00:03", "width": 64,
                  "height": 48, "fps": 10.0, "total_frames": 30, "file_format": "mp4"},
        "analysis": {"created_at": "2026-09-26", "settings_summary": "default"},
        "objects_summary": [],
        "tracked_objects": [],
        "faces": [],
        "timeline": [],
        "evidence_frames": [],
        "model_info": {"detector": "motion_fallback", "tracker": "iou", "facial_model": "mediapipe",
                       "classifier": "Not available", "metrics": {}},
        "conclusion": build_conclusion_text([], [], []),
    }
    path = generate_forensic_report(out, data)
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 500  # a real multi-section PDF, not an empty stub
    with open(path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


def test_report_generates_with_populated_data(tmp_path):
    out = str(tmp_path / "report_full.pdf")
    objects_summary = [{"class_name": "person", "count": 3, "first_seen": "00:00:04", "last_seen": "00:03:20"}]
    tracks = [{"track_id": 1, "class_name": "person", "first_timestamp": 4.0, "last_timestamp": 200.0,
               "duration_seconds": 196.0, "average_confidence": 0.91, "detection_count": 120}]
    faces = [{"face_id": "F1", "timestamp": 5.2, "landmark_confidence": 0.93,
              "quality_flags": [], "classifier_result": None}]
    timeline = [{"timestamp": "00:00:04", "description": "Person #1 entered", "confidence": 0.96}]
    data = {
        "case": {"case_id": "CASE-2026-002", "title": "Populated", "analyst": "Analyst"},
        "video": {"filename": "cctv.mp4", "duration_display": "00:03:20", "width": 1920,
                  "height": 1080, "fps": 25.0, "total_frames": 5000, "file_format": "mp4"},
        "analysis": {"created_at": "2026-09-26", "settings_summary": "conf=0.4"},
        "objects_summary": objects_summary,
        "tracked_objects": tracks,
        "faces": faces,
        "timeline": timeline,
        "evidence_frames": [],
        "model_info": {"detector": "yolo", "tracker": "bytetrack", "facial_model": "mediapipe face mesh",
                       "classifier": "random_forest-123", "metrics": {"accuracy": 0.88}},
        "conclusion": build_conclusion_text(objects_summary, tracks, faces),
    }
    path = generate_forensic_report(out, data)
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 1000
