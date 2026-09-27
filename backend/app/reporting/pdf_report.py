"""
Forensic PDF report generation using ReportLab (spec section 29).

`generate_forensic_report` takes plain dict/list structures (already
persisted, real analysis data — never invented here) and renders a
multi-section PDF: case info, video info, object summary, tracking,
facial analysis, timeline, evidence frames, model/evaluation info,
machine-generated conclusion, and the mandatory disclaimer.

Any section for which data is unavailable renders an explicit
"Not available" / "No X detected" line rather than being silently
omitted or padded with placeholder numbers.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                 Spacer, Table, TableStyle)

DISCLAIMER_TEXT = (
    "The output is intended as investigative/decision-support evidence and is "
    "not an automatic legal determination."
)

_styles = getSampleStyleSheet()
_styles.add(ParagraphStyle(name="TVTitle", fontSize=20, leading=24, spaceAfter=6, textColor=colors.HexColor("#1a1f2b")))
_styles.add(ParagraphStyle(name="TVSection", fontSize=13, leading=16, spaceBefore=14, spaceAfter=6,
                            textColor=colors.HexColor("#1a1f2b")))
_styles.add(ParagraphStyle(name="TVBody", fontSize=9.5, leading=13))
_styles.add(ParagraphStyle(name="TVSmall", fontSize=8, leading=11, textColor=colors.HexColor("#555555")))
_styles.add(ParagraphStyle(name="TVDemo", fontSize=9.5, leading=13, textColor=colors.HexColor("#8a5b00")))


def _table(data: List[List[str]], col_widths=None) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1f2b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f6f8")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def generate_forensic_report(output_path: str, report_data: Dict[str, Any]) -> str:
    """report_data expected shape (all keys optional except case/video):
    {
      "case": {...}, "video": {...}, "analysis": {...},
      "objects_summary": [{class_name,count,first_seen,last_seen}],
      "tracked_objects": [{track_id,class_name,first_timestamp,last_timestamp,
                            duration_seconds,average_confidence,detection_count}],
      "faces": [{face_id,timestamp,landmark_confidence,quality_flags,
                 geometric_features,classifier_result,similarity_score}],
      "timeline": [{timestamp,event_type,description,confidence}],
      "evidence_frames": [{evidence_id,timestamp,reason,image_path}],
      "model_info": {detector,tracker,facial_model,classifier,metrics:{...}},
      "demo_mode": bool,
      "conclusion": "..."  # machine-generated summary text
    }
    """
    buf_path = output_path
    doc = SimpleDocTemplate(buf_path, pagesize=A4,
                             topMargin=18 * mm, bottomMargin=18 * mm,
                             leftMargin=16 * mm, rightMargin=16 * mm)
    story = []
    case = report_data.get("case", {})
    video = report_data.get("video", {})
    analysis = report_data.get("analysis", {})

    story.append(Paragraph("TRACEVISION Forensic Analysis Report", _styles["TVTitle"]))
    if report_data.get("demo_mode"):
        story.append(Paragraph(
            "DEMO MODE \u2014 Results are simulated and must not be interpreted as real forensic analysis.",
            _styles["TVDemo"]))
    story.append(Spacer(1, 4 * mm))

    # A. Case information
    story.append(Paragraph("A. Case Information", _styles["TVSection"]))
    story.append(_table([
        ["Field", "Value"],
        ["Case ID", str(case.get("case_id", "Not available"))],
        ["Case Title", str(case.get("title", "Not available"))],
        ["Analyst", str(case.get("analyst", "Not available"))],
        ["Analysis Date", str(analysis.get("created_at", "Not available"))],
        ["Video Filename", str(video.get("filename", "Not available"))],
        ["Video Duration", str(video.get("duration_display", "Not available"))],
    ], col_widths=[55 * mm, 110 * mm]))

    # B. Video information
    story.append(Paragraph("B. Video Information", _styles["TVSection"]))
    story.append(_table([
        ["Field", "Value"],
        ["Resolution", f"{video.get('width', '?')}x{video.get('height', '?')}"],
        ["Frame Rate", f"{video.get('fps', 'Not available')} fps"],
        ["Total Frames", str(video.get("total_frames", "Not available"))],
        ["File Format", str(video.get("file_format", "Not available"))],
        ["Processing Settings", str(analysis.get("settings_summary", "Default"))],
    ], col_widths=[55 * mm, 110 * mm]))

    # C. Object detection summary
    story.append(Paragraph("C. Object Detection Summary", _styles["TVSection"]))
    objects_summary = report_data.get("objects_summary") or []
    if objects_summary:
        rows = [["Object Class", "Count", "First Seen", "Last Seen"]]
        for o in objects_summary:
            rows.append([o.get("class_name", "?"), str(o.get("count", 0)),
                         o.get("first_seen", "-"), o.get("last_seen", "-")])
        story.append(_table(rows, col_widths=[55 * mm, 30 * mm, 40 * mm, 40 * mm]))
    else:
        story.append(Paragraph("0 objects detected.", _styles["TVBody"]))

    # D. Tracking information
    story.append(Paragraph("D. Tracking Information", _styles["TVSection"]))
    tracks = report_data.get("tracked_objects") or []
    if tracks:
        rows = [["Track ID", "Class", "First", "Last", "Duration (s)", "Avg Conf."]]
        for t in tracks:
            rows.append([str(t.get("track_id")), t.get("class_name", "?"),
                         str(t.get("first_timestamp")), str(t.get("last_timestamp")),
                         str(t.get("duration_seconds")), str(t.get("average_confidence"))])
        story.append(_table(rows, col_widths=[20 * mm, 30 * mm, 25 * mm, 25 * mm, 30 * mm, 35 * mm]))
    else:
        story.append(Paragraph("No tracked objects.", _styles["TVBody"]))

    # E. Facial analysis
    story.append(Paragraph("E. Facial Analysis", _styles["TVSection"]))
    faces = report_data.get("faces") or []
    if faces:
        for face in faces:
            story.append(Paragraph(
                f"Face {face.get('face_id')} \u2014 t={face.get('timestamp')}s, "
                f"landmark confidence={face.get('landmark_confidence', 'Not available')}, "
                f"flags={', '.join(face.get('quality_flags', [])) or 'none'}",
                _styles["TVBody"]))
            cr = face.get("classifier_result")
            story.append(Paragraph(
                f"Classifier result: {cr if cr else 'No facial comparison available.'}",
                _styles["TVSmall"]))
    else:
        story.append(Paragraph("No faces were detected.", _styles["TVBody"]))

    # F. Event timeline
    story.append(Paragraph("F. Event Timeline", _styles["TVSection"]))
    timeline = report_data.get("timeline") or []
    if timeline:
        rows = [["Timestamp", "Event", "Confidence"]]
        for e in timeline:
            rows.append([e.get("timestamp", "-"), e.get("description", "-"), str(e.get("confidence", "-"))])
        story.append(_table(rows, col_widths=[30 * mm, 105 * mm, 30 * mm]))
    else:
        story.append(Paragraph("No timeline events were recorded.", _styles["TVBody"]))

    # G. Evidence frames
    story.append(Paragraph("G. Evidence Frames", _styles["TVSection"]))
    evidence = report_data.get("evidence_frames") or []
    if evidence:
        for ev in evidence:
            story.append(Paragraph(
                f"Evidence {ev.get('evidence_id')} \u2014 t={ev.get('timestamp')}s \u2014 reason: {ev.get('reason')}",
                _styles["TVBody"]))
            img_path = ev.get("image_path")
            if img_path:
                try:
                    story.append(Image(img_path, width=90 * mm, height=50 * mm))
                except Exception:
                    story.append(Paragraph("(evidence image could not be embedded)", _styles["TVSmall"]))
    else:
        story.append(Paragraph("No evidence frames available.", _styles["TVBody"]))

    # H. Model/evaluation information
    story.append(Paragraph("H. Model / Evaluation Information", _styles["TVSection"]))
    model_info = report_data.get("model_info") or {}
    metrics = model_info.get("metrics") or {}
    story.append(_table([
        ["Field", "Value"],
        ["Object Detection Model", str(model_info.get("detector", "Not available"))],
        ["Tracking Method", str(model_info.get("tracker", "Not available"))],
        ["Facial Analysis Model", str(model_info.get("facial_model", "Not available"))],
        ["ML Classifier", str(model_info.get("classifier", "Not available"))],
        ["Accuracy", str(metrics.get("accuracy", "Not available"))],
        ["Precision", str(metrics.get("precision", "Not available"))],
        ["Recall", str(metrics.get("recall", "Not available"))],
        ["F1-score", str(metrics.get("f1_score", "Not available"))],
    ], col_widths=[55 * mm, 110 * mm]))

    # I. Conclusion
    story.append(Paragraph("I. Conclusion (Machine-Generated Summary)", _styles["TVSection"]))
    story.append(Paragraph(report_data.get("conclusion") or "No summary was generated.", _styles["TVBody"]))

    # J. Disclaimer
    story.append(Paragraph("J. Disclaimer", _styles["TVSection"]))
    story.append(Paragraph(DISCLAIMER_TEXT, _styles["TVSmall"]))

    doc.build(story)
    return buf_path


def build_conclusion_text(objects_summary: List[dict], tracks: List[dict], faces: List[dict]) -> str:
    """Deterministic, template-based machine-generated summary — no LLM call,
    no invented facts; it only restates counts that were actually computed."""
    n_objects = sum(o.get("count", 0) for o in objects_summary)
    n_tracks = len(tracks)
    n_faces = len(faces)
    parts = [
        f"This machine-generated summary reflects {n_objects} object detection(s) across "
        f"{n_tracks} tracked object(s), and {n_faces} face detection(s) in the analyzed video."
    ]
    if n_faces == 0:
        parts.append("No facial analysis was possible because no faces were detected.")
    if n_objects == 0:
        parts.append("No objects belonging to the supported detection classes were found in this video.")
    parts.append(
        "All figures above were produced by the automated analysis pipeline and require human "
        "review before being used in any investigative decision."
    )
    return " ".join(parts)
