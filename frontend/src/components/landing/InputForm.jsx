import { useState } from "react";
import HandleChip from "../shared/HandleChip";

export default function InputForm({
  brandUrl,
  competitorUrls,
  linksLocked,
  isRunning,
  onBrandUrlChange,
  onCompetitorUrlsChange,
  onLock,
  onUnlock,
  onRun,
}) {
  // single source of truth
  const [competitorText, setCompetitorText] = useState(
    competitorUrls.join("\n")
  );

  const handleLock = () => {
    const urls = competitorText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    onCompetitorUrlsChange(urls); // update parent ONCE
    onLock();
  };

  return (
    <section className="mx-auto mt-12 w-full max-w-2xl px-6 pb-16">
      {!linksLocked ? (
        <div className="glass-card rounded-2xl border border-brand-border p-6">
          <h3 className="text-lg font-bold text-white">📎 Instagram Links</h3>

          <label className="mt-5 block text-sm font-medium text-slate-300">
            Your Instagram URL
            <input
              value={brandUrl}
              onChange={(e) => onBrandUrlChange(e.target.value)}
              placeholder="https://www.instagram.com/your_handle/"
              className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-slate-100 outline-none placeholder:text-brand-muted focus:border-blue-500 focus:ring-2 focus:ring-blue-500/40"
            />
          </label>

          <label className="mt-4 block text-sm font-medium text-slate-300">
            Competitor URLs (one per line)
            <textarea
              rows={4}
              value={competitorText}
              onChange={(e) => setCompetitorText(e.target.value)}
              placeholder={[
                "https://www.instagram.com/competitor_one/",
                "https://www.instagram.com/competitor_two/",
              ].join("\n")}
              className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-slate-100 outline-none placeholder:text-brand-muted focus:border-blue-500 focus:ring-2 focus:ring-blue-500/40"
            />
          </label>

          <button
            type="button"
            onClick={handleLock}
            disabled={!brandUrl || competitorText.trim() === ""}
            className="mt-5 w-full rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 px-4 py-2.5 font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Lock Links & Continue →
          </button>
        </div>
      ) : (
        <>
          <div className="glass-card rounded-2xl border border-brand-border p-6">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-white">
                ✅ Locked Handles
              </h3>
              <button
                type="button"
                onClick={onUnlock}
                className="rounded-md border border-slate-600 px-3 py-1 text-sm text-slate-300 hover:text-white"
              >
                ✏️ Edit
              </button>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <HandleChip url={brandUrl} isBrand />
              {competitorUrls.map((url, index) => (
                <HandleChip key={url + index} url={url} />
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={onRun}
            disabled={isRunning}
            className="mx-auto mt-6 block w-full max-w-md rounded-lg bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500 px-5 py-3 text-base font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
          >
            🚀 Generate Strategy
          </button>
        </>
      )}
    </section>
  );
}