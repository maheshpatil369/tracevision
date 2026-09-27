import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { Case } from "../types";
import StatusBadge from "../components/StatusBadge";
import EmptyState from "../components/EmptyState";

export default function Cases() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ case_number: "", title: "", description: "" });
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api
      .get<{ items: Case[] }>("/cases")
      .then((res) => setCases(res.items))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/cases", form);
      setForm({ case_number: "", title: "", description: "" });
      setShowForm(false);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Cases</h1>
        <button className="tv-btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "New case"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={submit} className="tv-card space-y-3 max-w-lg">
          {error && <div className="text-sm text-red-600">{error}</div>}
          <div>
            <label className="text-xs text-gray-500">Case number</label>
            <input
              required
              className="w-full border rounded px-2 py-1 text-sm"
              placeholder="CASE-2026-001"
              value={form.case_number}
              onChange={(e) => setForm({ ...form, case_number: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">Title</label>
            <input
              required
              className="w-full border rounded px-2 py-1 text-sm"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">Description</label>
            <textarea
              className="w-full border rounded px-2 py-1 text-sm"
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <button className="tv-btn-primary" type="submit">
            Create case
          </button>
        </form>
      )}

      <div className="tv-card p-0 overflow-hidden">
        {loading ? (
          <div className="p-6 text-gray-500 text-sm">Loading…</div>
        ) : cases.length === 0 ? (
          <EmptyState message="No cases yet." hint="Create a case to begin." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-2">Case</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-left px-4 py-2">Videos</th>
                <th className="text-left px-4 py-2">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {cases.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <Link to={`/cases/${c.id}`} className="font-medium hover:underline">
                      {c.case_number}
                    </Link>
                    <div className="text-gray-500 text-xs">{c.title}</div>
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-2">{c.video_count}</td>
                  <td className="px-4 py-2 text-gray-500">{new Date(c.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
