import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../services/api";
import {
  Analysis, EvidenceFrame, Face, ObjectSummary, ProcessingJob, TimelineEvent, TrackedObject,
} from "../types";
import StatusBadge from "../components/StatusBadge";
import EmptyState from "../components/EmptyState";

type TabKey = "overview" | "objects" | "tracks" | "faces" | "evidence" | "timeline";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "objects", label: "Objects" },
  { key: "tracks", label: "Tracked objects" },
  { key: "faces", label: "Faces" },
  { key: "evidence", label: "Evidence" },
  { key: "timeline", label: "Timeline" },
];

export default function AnalysisDetail() {
  const { analysisId } = useParams();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [job, setJob] = useState<ProcessingJob | null>(null);
  const [objects, setObjects] = useState<ObjectSummary[]>([]);
  const [tracks, setTracks] = useState<TrackedObject[]>([]);
  const [faces, setFaces] = useState<Face[]>([]);
  const [evidence, setEvidence] = useState<EvidenceFrame[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [tab, setTab] = useState<TabKey>("overview");
  const pollRef = useRef<number | null>(null);

  const loadStatus = async () => {
    if (!analysisId) return;
    const status = await api.get<{ analysis: Analysis; job: ProcessingJob | null }>(
      `/analyses/${analysisId}/status`
    );
    setAnalysis(status.analysis);
    setJob(status.job);
    return status.analysis;
  };

  const loadForensicData = async () => {
    if (!analysisId) return;
    const [o, t, f, e, tl] = await Promise.all([
      api.get<ObjectSummary[]>(`/objects/by-analysis/${analysisId}`),
      api.get<TrackedObject[]>(`/tracks/by-analysis/${analysisId}`),
      api.get<Face[]>(`/faces/by-analysis/${analysisId}`),
      api.get<EvidenceFrame[]>(`/evidence/by-analysis/${analysisId}`),
      api.get<TimelineEvent[]>(`/timeline/by-analysis/${analysisId}`),
    ]);
    setObjects(o);
    setTracks(t);
    setFaces(f);
    setEvidence(e);
    setTimeline(tl);
  };

  useEffect(() => {
    loadStatus().then((a) => {
      if (a && (a.status === "completed" || a.status === "failed" || a.status === "cancelled")) {
        loadForensicData();
      }
    });
  }, [analysisId]);

  useEffect(() => {
    if (!analysis) return;
    if (analysis.status === "queued" || analysis.status === "processing") {
      pollRef.current = window.setInterval(async () => {
        const a = await loadStatus();
        if (a && a.status !== "queued" && a.status !== "processing") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          loadForensicData();
        }
      }, 2000);
      return () => {
        if (pollRef.current) window.clearInterval(pollRef.current);
      };
    }
  }, [analysis?.status]);

  const generateReport = async () => {
    if (!analysisId) return;
    await api.post("/reports", { analysis_id: analysisId, demo_mode: false });
    alert("Report generation started. Check the case's Reports section for the download link.");
  };

  if (!analysis) return <div className="p-6 text-gray-500">Loading analysis…</div>;

  return (
    <div className="p-6 space-y-4">
      <div>
        <div className="text-xs text-gray-400">Analysis {analysis.id.slice(0, 8)}</div>
        <div className="flex items-center gap-3 mt-1">
          <h1 className="text-xl font-semibold">Analysis details</h1>
          <StatusBadge status={analysis.status} />
        </div>
        <div className="text-xs text-gray-500 mt-1">{analysis.settings_summary}</div>
      </div>

      {(analysis.status === "queued" || analysis.status === "processing") && (
        <div className="tv-card">
          <div className="text-sm font-medium mb-2">
            Processing: {job?.current_stage?.replace(/_/g, " ") || "starting…"}
          </div>
          <div className="w-full bg-gray-100 rounded h-2 overflow-hidden">
            <div
              className="bg-ink h-2 transition-all"
              style={{ width: `${job?.progress_percent ?? 0}%` }}
            />
          </div>
          <div className="text-xs text-gray-400 mt-1">{job?.progress_percent ?? 0}%</div>
        </div>
      )}

      {analysis.status === "failed" && (
        <div className="tv-card border-red-200 bg-red-50 text-sm text-red-700">
          Analysis failed: {analysis.error_message || "Unknown error"}
        </div>
      )}

      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-sm border-b-2 -mb-px ${
              tab === t.key ? "border-ink font-medium" : "border-transparent text-gray-500 hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="tv-card space-y-3">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Detector backend:</span> {analysis.detector_backend || "Not available"}
            </div>
            <div>
              <span className="text-gray-500">Tracker:</span> {analysis.tracker_name}
            </div>
            <div>
              <span className="text-gray-500">Started:</span>{" "}
              {analysis.started_at ? new Date(analysis.started_at).toLocaleString() : "-"}
            </div>
            <div>
              <span className="text-gray-500">Completed:</span>{" "}
              {analysis.completed_at ? new Date(analysis.completed_at).toLocaleString() : "-"}
            </div>
          </div>
          <button className="tv-btn-primary" onClick={generateReport} disabled={analysis.status !== "completed"}>
            Generate forensic report (PDF)
          </button>
        </div>
      )}

      {tab === "objects" && (
        <div className="tv-card p-0 overflow-hidden">
          {objects.length === 0 ? (
            <EmptyState message="0 objects detected." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="text-left px-4 py-2">Object</th>
                  <th className="text-left px-4 py-2">Count</th>
                  <th className="text-left px-4 py-2">First seen</th>
                  <th className="text-left px-4 py-2">Last seen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {objects.map((o) => (
                  <tr key={o.class_name}>
                    <td className="px-4 py-2 capitalize">{o.class_name}</td>
                    <td className="px-4 py-2">{o.count}</td>
                    <td className="px-4 py-2">{o.first_seen}</td>
                    <td className="px-4 py-2">{o.last_seen}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "tracks" && (
        <div className="tv-card p-0 overflow-hidden">
          {tracks.length === 0 ? (
            <EmptyState message="No tracked objects." />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="text-left px-4 py-2">Object</th>
                  <th className="text-left px-4 py-2">First</th>
                  <th className="text-left px-4 py-2">Last</th>
                  <th className="text-left px-4 py-2">Duration</th>
                  <th className="text-left px-4 py-2">Avg conf.</th>
                  <th className="text-left px-4 py-2">Detections</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tracks.map((t) => (
                  <tr key={t.id}>
                    <td className="px-4 py-2">{t.display_label}</td>
                    <td className="px-4 py-2">{t.first_timestamp.toFixed(1)}s</td>
                    <td className="px-4 py-2">{t.last_timestamp.toFixed(1)}s</td>
                    <td className="px-4 py-2">{t.duration_seconds.toFixed(1)}s</td>
                    <td className="px-4 py-2">{(t.average_confidence * 100).toFixed(0)}%</td>
                    <td className="px-4 py-2">{t.detection_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "faces" && (
        <div className="space-y-3">
          {faces.length === 0 ? (
            <div className="tv-card">
              <EmptyState message="No faces were detected." />
            </div>
          ) : (
            faces.map((f) => (
              <div key={f.id} className="tv-card text-sm">
                <div className="flex items-center justify-between">
                  <div>
                    Face at {f.timestamp.toFixed(2)}s — landmark confidence:{" "}
                    {f.landmark_confidence != null ? `${(f.landmark_confidence * 100).toFixed(0)}%` : "Not available"}
                  </div>
                  {f.quality_flags.length > 0 && (
                    <div className="text-xs text-amber-700">{f.quality_flags.join(", ")}</div>
                  )}
                </div>
                {f.geometric_features && (
                  <details className="mt-2">
                    <summary className="text-xs text-gray-500 cursor-pointer">Geometric features</summary>
                    <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
                      <div>
                        <div className="font-medium mb-1">Euclidean distances</div>
                        {Object.entries(f.geometric_features.euclidean).map(([k, v]) => (
                          <div key={k}>
                            {k}: {v}
                          </div>
                        ))}
                      </div>
                      <div>
                        <div className="font-medium mb-1">Ratios</div>
                        {Object.entries(f.geometric_features.ratios).map(([k, v]) => (
                          <div key={k}>
                            {k}: {v ?? "Not available"}
                          </div>
                        ))}
                      </div>
                    </div>
                  </details>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {tab === "evidence" && (
        <div className="grid md:grid-cols-2 gap-4">
          {evidence.length === 0 ? (
            <div className="tv-card col-span-2">
              <EmptyState message="No evidence frames available." />
            </div>
          ) : (
            evidence.map((e) => (
              <div key={e.id} className="tv-card">
                <img
                  src={`/media/evidence/${e.annotated_frame_path?.split("/").slice(-2).join("/")}`}
                  alt={`Evidence at ${e.timestamp}s`}
                  className="w-full rounded border border-gray-200 mb-2"
                  onError={(ev) => ((ev.target as HTMLImageElement).style.display = "none")}
                />
                <div className="text-sm">
                  <span className="font-medium">{e.reason.replace(/_/g, " ")}</span> at {e.timestamp.toFixed(2)}s
                </div>
                <div className="text-xs text-gray-500">
                  {e.object_types.join(", ")} · confidence{" "}
                  {e.confidence_values.map((c) => `${(c * 100).toFixed(0)}%`).join(", ")}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "timeline" && (
        <div className="tv-card">
          {timeline.length === 0 ? (
            <EmptyState message="No timeline events were recorded." />
          ) : (
            <ol className="relative border-l border-gray-200 ml-2">
              {timeline.map((e) => (
                <li key={e.id} className="mb-4 ml-4">
                  <div className="absolute w-2 h-2 bg-ink rounded-full -left-1 mt-1.5" />
                  <time className="text-xs text-gray-400">{e.timestamp}</time>
                  <div className="text-sm">
                    {e.description}
                    {e.confidence != null && (
                      <span className="text-xs text-gray-400 ml-2">{(e.confidence * 100).toFixed(0)}%</span>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
