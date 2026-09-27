const COLORS: Record<string, string> = {
  open: "bg-blue-100 text-blue-800",
  in_progress: "bg-amber-100 text-amber-800",
  closed: "bg-gray-200 text-gray-700",
  archived: "bg-gray-100 text-gray-500",
  queued: "bg-gray-100 text-gray-600",
  processing: "bg-amber-100 text-amber-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-gray-200 text-gray-600",
  pending: "bg-gray-100 text-gray-600",
  generating: "bg-amber-100 text-amber-800",
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = COLORS[status] || "bg-gray-100 text-gray-700";
  return <span className={`tv-badge ${cls}`}>{status.replace("_", " ")}</span>;
}
