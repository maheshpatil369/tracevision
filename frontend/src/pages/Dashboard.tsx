import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { DashboardData } from "../types";
import StatusBadge from "../components/StatusBadge";

const STAT_LABELS: [keyof DashboardData, string][] = [
  ["total_cases", "Cases"],
  ["total_videos_processed", "Videos processed"],
  ["total_analyses", "Analyses"],
  ["total_detected_objects", "Detected objects"],
  ["total_tracked_objects", "Tracked objects"],
  ["total_detected_faces", "Detected faces"],
  ["total_evidence_frames", "Evidence frames"],
  ["total_reports_generated", "Reports generated"],
];

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<DashboardData>("/dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-6 text-red-600">Failed to load dashboard: {error}</div>;
  if (!data) return <div className="p-6 text-gray-500">Loading dashboard…</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {STAT_LABELS.map(([key, label]) => (
          <div key={key} className="tv-card">
            <div className="text-2xl font-semibold">{data[key] as number}</div>
            <div className="text-xs text-gray-500 mt-1">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="tv-card">
          <h2 className="font-medium mb-3">Recent cases</h2>
          {data.recent_cases.length === 0 ? (
            <p className="text-sm text-gray-500">No cases yet. Create a case to begin.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {data.recent_cases.map((c) => (
                <li key={c.id} className="py-2 flex items-center justify-between text-sm">
                  <Link to={`/cases/${c.id}`} className="hover:underline">
                    {c.case_number} — {c.title}
                  </Link>
                  <StatusBadge status={c.status} />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="tv-card">
          <h2 className="font-medium mb-3">Recent analyses</h2>
          {data.recent_analyses.length === 0 ? (
            <p className="text-sm text-gray-500">No analysis has been run.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {data.recent_analyses.map((a) => (
                <li key={a.id} className="py-2 flex items-center justify-between text-sm">
                  <Link to={`/analyses/${a.id}`} className="hover:underline">
                    Analysis {a.id.slice(0, 8)}
                  </Link>
                  <StatusBadge status={a.status} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
