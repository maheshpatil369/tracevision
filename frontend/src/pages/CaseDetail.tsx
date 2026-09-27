import { ChangeEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../services/api";
import { Analysis, Case, Report, Video } from "../types";
import StatusBadge from "../components/StatusBadge";
import EmptyState from "../components/EmptyState";

export default function CaseDetail() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [analysesByVideo, setAnalysesByVideo] = useState<Record<string, Analysis[]>>({});
  const [reports, setReports] = useState<Report[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadAll = () => {
    if (!caseId) return;
    api.get<Case>(`/cases/${caseId}`).then(setCaseData);
    api.get<Video[]>(`/videos/by-case/${caseId}`).then(async (vids) => {
      setVideos(vids);
      const entries = await Promise.all(
        vids.map(async (v) => [v.id, await api.get<Analysis[]>(`/analyses/by-video/${v.id}`)] as const)
      );
      setAnalysesByVideo(Object.fromEntries(entries));
    });
    api.get<Report[]>(`/reports/by-case/${caseId}`).then(setReports);
  };

  useEffect(loadAll, [caseId]);

  const handleUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !caseId) return;
    setUploading(true);
    setUploadError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      await api.upload(`/videos/upload?case_id=${caseId}`, form);
      loadAll();
    } catch (err: any) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };

const startAnalysis = async (videoId: string) => {
  await api.post(`/analyses?video_id=${videoId}`, { tracker: "auto" });
  loadAll();
};

  const generateReport = async (analysisId: string) => {
    await api.post("/reports", { analysis_id: analysisId, demo_mode: false });
    loadAll();
  };

  if (!caseData) return <div className="p-6 text-gray-500">Loading case…</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="text-xs text-gray-400">
          <Link to="/cases" className="hover:underline">
            Cases
          </Link>{" "}
          / {caseData.case_number}
        </div>
        <div className="flex items-center gap-3 mt-1">
          <h1 className="text-xl font-semibold">{caseData.title}</h1>
          <StatusBadge status={caseData.status} />
        </div>
        {caseData.description && <p className="text-sm text-gray-600 mt-1">{caseData.description}</p>}
      </div>

      <section className="tv-card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Videos</h2>
          <label className="tv-btn-secondary cursor-pointer">
            {uploading ? "Uploading…" : "Upload video"}
            <input type="file" accept=".mp4,.avi,.mov,.mkv,.webm" className="hidden" onChange={handleUpload} />
          </label>
        </div>
        {uploadError && <div className="text-sm text-red-600">{uploadError}</div>}

        {videos.length === 0 ? (
          <EmptyState message="No videos uploaded." />
        ) : (
          <div className="space-y-4">
            {videos.map((v) => (
              <div key={v.id} className="border border-gray-200 rounded p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{v.original_filename}</div>
                    <div className="text-xs text-gray-500">
                      {v.width}x{v.height} · {v.fps.toFixed(1)} fps · {v.total_frames} frames ·{" "}
                      {v.duration_seconds.toFixed(1)}s · {(v.file_size_bytes / 1e6).toFixed(1)} MB
                    </div>
                  </div>
                  <button className="tv-btn-primary" onClick={() => startAnalysis(v.id)}>
                    Start analysis
                  </button>
                </div>

                <div className="mt-2">
                  {(analysesByVideo[v.id] || []).length === 0 ? (
                    <p className="text-xs text-gray-400">No analysis has been run.</p>
                  ) : (
                    <ul className="text-sm divide-y divide-gray-100">
                      {analysesByVideo[v.id].map((a) => (
                        <li key={a.id} className="py-1.5 flex items-center justify-between">
                          <Link to={`/analyses/${a.id}`} className="hover:underline">
                            Analysis {a.id.slice(0, 8)}
                            <span className="text-xs text-gray-400 ml-2">{a.settings_summary}</span>
                          </Link>
                          <div className="flex items-center gap-2">
                            <StatusBadge status={a.status} />
                            {a.status === "completed" && (
                              <button className="tv-btn-secondary" onClick={() => generateReport(a.id)}>
                                Generate report
                              </button>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="tv-card space-y-3">
        <h2 className="font-medium">Reports</h2>
        {reports.length === 0 ? (
          <EmptyState message="No reports generated yet." />
        ) : (
          <ul className="text-sm divide-y divide-gray-100">
            {reports.map((r) => (
              <li key={r.id} className="py-1.5 flex items-center justify-between">
                <span>
                  {r.filename || `Report v${r.version}`} <StatusBadge status={r.status} />
                </span>
                {r.status === "completed" && (
                  <a className="tv-btn-secondary" href={`/api/reports/${r.id}/download`} target="_blank" rel="noreferrer">
                    Download PDF
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
