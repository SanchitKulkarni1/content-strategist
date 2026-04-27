import { useMemo, useState } from "react";
import TrendPill from "../../shared/TrendPill";

function labelize(value) {
  return value || "N/A";
}

function parseHashtags(value) {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    return value
      .split(/\s+/)
      .map((item) => item.trim())
      .filter((item) => item.startsWith("#"));
  }
  return [];
}

export default function PostPrompts({
  data,
  trends,
  activeTrend,
  onTrendSelect,
  onRegenerate,
  isRegenerating,
}) {
  const [customTrend, setCustomTrend] = useState("");

  const posts = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  return (
    <div className="mt-6 space-y-5">
      <section className="glass-card rounded-xl border border-brand-border p-4">
        <p className="text-xs text-brand-muted">Filter by Trend</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {trends.map((trend) => (
            <TrendPill
              key={trend}
              trend={trend}
              active={activeTrend === trend}
              onClick={onTrendSelect}
            />
          ))}
        </div>

        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            value={customTrend}
            onChange={(event) => setCustomTrend(event.target.value)}
            placeholder="Enter custom trend"
            className="flex-1 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-brand-muted focus:border-blue-500 focus:ring-2 focus:ring-blue-500/40"
          />
          <button
            type="button"
            disabled={isRegenerating || !customTrend.trim()}
            onClick={() => {
              onTrendSelect(customTrend.trim());
              onRegenerate(customTrend.trim());
              setCustomTrend("");
            }}
            className="rounded-lg bg-blue-500 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-400 disabled:opacity-50"
          >
            🔄 Regenerate
          </button>
        </div>

        {activeTrend ? (
          <span className="mt-3 inline-flex rounded-full border border-blue-500/40 bg-blue-500/20 px-2.5 py-1 text-xs text-blue-200">
            Active: {activeTrend}
          </span>
        ) : null}
      </section>

      <div className="border-t border-slate-800" />

      <section className="space-y-3">
        {posts.map((post, idx) => (
          <details key={`post-${idx}`} className="rounded-lg border border-slate-700 bg-slate-800/50 p-3">
            <summary className="cursor-pointer list-none text-sm font-semibold text-slate-100">
              Post #{idx + 1}: {labelize(post.format)} - {String(post.gap_addressed || "").slice(0, 45)}
            </summary>

            <div className="mt-3 space-y-4 border-t border-slate-700 pt-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-brand-muted">Format</p>
                  <p className="text-sm text-white">{labelize(post.format)}</p>
                </div>
                <div>
                  <p className="text-xs text-brand-muted">Gap Addressed</p>
                  <p className="text-sm text-white">{labelize(post.gap_addressed)}</p>
                </div>
                <div>
                  <p className="text-xs text-brand-muted">Best Time</p>
                  <p className="text-sm text-white">{labelize(post.best_time_to_post)}</p>
                </div>
                <div>
                  <p className="text-xs text-brand-muted">CTA</p>
                  <p className="text-sm text-white">{labelize(post.cta)}</p>
                </div>
              </div>

              <blockquote className="border-l-[3px] border-violet-500 pl-3 italic text-slate-200">
                {labelize(post.hook)}
              </blockquote>
              <blockquote className="border-l-[3px] border-blue-500 pl-3 text-slate-200">
                {labelize(post.concept)}
              </blockquote>
              <blockquote className="border-l-[3px] border-green-500 pl-3 text-slate-200">
                {labelize(post.why_this_wins)}
              </blockquote>

              <pre className="whitespace-pre-wrap rounded-lg border border-slate-700 bg-slate-950 p-4 font-mono text-xs text-slate-200">
                {labelize(post.caption_template || post.caption)}
              </pre>

              <div className="flex flex-wrap gap-2">
                {parseHashtags(post.hashtags).map((tag, tagIndex) => (
                  <span key={`tag-${idx}-${tagIndex}`} className="rounded bg-slate-700 px-2 py-0.5 text-xs text-blue-300">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </details>
        ))}
      </section>
    </div>
  );
}
