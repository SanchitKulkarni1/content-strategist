import HandleChip from "../shared/HandleChip";

export default function TopBar({ brandUrl, competitorUrls, onEdit, onRerun, isRunning }) {
  return (
    <header className="fixed inset-x-0 top-0 z-30 border-b border-slate-800 bg-slate-900/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-6">
        <div className="flex flex-wrap items-center gap-2">
          <HandleChip url={brandUrl} isBrand />
          {competitorUrls.map((url) => (
            <HandleChip key={url} url={url} />
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onEdit}
            className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:text-white"
          >
            ✏️ Edit
          </button>
          <button
            type="button"
            onClick={onRerun}
            disabled={isRunning}
            className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:text-white disabled:opacity-50"
          >
            🔄 Re-run
          </button>
        </div>
      </div>
    </header>
  );
}
