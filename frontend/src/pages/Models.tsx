import { useEffect, useState } from "react";
import { api } from "../services/api";
import { ModelRun } from "../types";
import EmptyState from "../components/EmptyState";

export default function Models() {
  const [models, setModels] = useState<ModelRun[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .get<ModelRun[]>("/models")
      .then(setModels)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Models &amp; evaluation</h1>
      <p className="text-sm text-gray-500 max-w-2xl">
        Trained facial-comparison classifiers and their real evaluation metrics. Metrics are computed
        from an actual train/test split — a field shows <em>"Not available"</em> rather than an invented
        number when a metric could not be computed. Training runs are started via{" "}
        <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">POST /api/models/train</code> — see
        docs/machine-learning.md for the request shape and how to supply labeled feature vectors.
      </p>

      <div className="tv-card p-0 overflow-hidden">
        {loading ? (
          <div className="p-6 text-gray-500 text-sm">Loading…</div>
        ) : models.length === 0 ? (
          <EmptyState
            message="No trained models yet."
            hint="Train one via POST /api/models/train (see docs/machine-learning.md)."
          />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-2">Version</th>
                <th className="text-left px-4 py-2">Algorithm</th>
                <th className="text-left px-4 py-2">Accuracy</th>
                <th className="text-left px-4 py-2">Precision</th>
                <th className="text-left px-4 py-2">Recall</th>
                <th className="text-left px-4 py-2">F1</th>
                <th className="text-left px-4 py-2">Samples</th>
                <th className="text-left px-4 py-2">Trained</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {models.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-2 font-mono text-xs">{m.model_version}</td>
                  <td className="px-4 py-2">{m.algorithm}</td>
                  <td className="px-4 py-2">{m.accuracy}</td>
                  <td className="px-4 py-2">{m.precision}</td>
                  <td className="px-4 py-2">{m.recall}</td>
                  <td className="px-4 py-2">{m.f1_score}</td>
                  <td className="px-4 py-2">{m.training_samples}</td>
                  <td className="px-4 py-2 text-gray-500">{new Date(m.trained_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
