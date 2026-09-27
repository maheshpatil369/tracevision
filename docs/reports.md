# Forensic Reports

`app/reporting/pdf_report.py:generate_forensic_report()` renders a
ReportLab PDF with every section spec 29 requires (A-J). See
`backend/tests/test_pdf_report.py` (passing during development, including
against a fully-empty-data case — every section still renders a real,
honest sentence like "0 objects detected." instead of a blank page).

## Data assembly

`app/services/report_service.py:ReportService.build_report_data()` queries
every relevant table for one `analysis_id` and shapes it into exactly the
dict `generate_forensic_report()` expects — this is the one place that
translates ORM rows into report content, so the PDF and the API's JSON
responses can never silently diverge in what they claim about an analysis.

## Filenames and versioning

`TRACEVISION_<case_number>_ANALYSIS-<short_id>_v<version>.pdf` —
`version` increments per `analysis_id` so `POST /api/reports` run twice
produces v1 then v2, never overwriting history. `GET /api/reports/by-case/
{case_id}` lists every version generated.

## Demo mode

`POST /api/reports {"demo_mode": true}` stamps the PDF's first page with
*"DEMO MODE — Results are simulated and must not be interpreted as real
forensic analysis."* This flag does not change what data is queried — it
only controls the disclosure banner. Actually generating simulated
detection data for a demo run is not implemented in this build (there is no
synthetic-video-generator); `demo_mode` exists so a future demo-data seeder
can flip it on without any report-generation code changes.
