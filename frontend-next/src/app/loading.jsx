export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-(--surface)">
      <div className="flex flex-col items-center gap-4">
        <div className="loading-spinner w-10 h-10" />
        <p className="text-sm text-(--text-muted)">Loading&hellip;</p>
      </div>
    </div>
  );
}
