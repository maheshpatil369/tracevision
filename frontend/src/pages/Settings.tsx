import { useEffect, useState } from "react";
import { api } from "../services/api";

interface HealthChecks {
  status: string;
  checks: Record<string, unknown>;
  app_version: string;
}

export default function Settings() {
  const [health, setHealth] = useState<HealthChecks | null>(null);

  useEffect(() => {
    api.get<HealthChecks>("/health").then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div className="p-6 space-y-4 max-w-2xl">
      <h1 className="text-xl font-semibold">Settings</h1>
      <p className="text-sm text-gray-500">
        Runtime configuration is controlled entirely through environment variables (see{" "}
        <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">.env.example</code> at the project
        root) — detection confidence, frame sampling interval, tracker choice, upload limits, storage
        paths, and model file locations. This page shows the live health/status of the running
        backend; it does not let you edit environment variables from the browser (spec section 34
        keeps configuration in `.env`, not the UI, to avoid drift between what's configured and what's
        running).
      </p>

      <div className="tv-card">
        <h2 className="font-medium mb-3">System health</h2>
        {!health ? (
          <div className="text-sm text-gray-500">Could not reach the backend health endpoint.</div>
        ) : (
          <pre className="text-xs bg-gray-50 rounded p-3 overflow-x-auto">
            {JSON.stringify(health, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
