export default function EmptyState({ message, hint }: { message: string; hint?: string }) {
  return (
    <div className="text-center py-16 text-gray-500">
      <div className="text-sm font-medium">{message}</div>
      {hint && <div className="text-xs mt-1 text-gray-400">{hint}</div>}
    </div>
  );
}
