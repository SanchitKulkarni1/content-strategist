import Card from "../../shared/Card";

function scoreInfo(gap) {
  const raw = gap?.overall_score;
  const score = typeof raw === "number" ? raw : Number(raw?.score || 0);

  if (score < 4) return { score, badge: "Low", className: "bg-red-500/20 text-red-300" };
  if (score < 7) return { score, badge: "Medium", className: "bg-amber-500/20 text-amber-300" };
  return { score, badge: "Strong", className: "bg-green-500/20 text-green-300" };
}

function weaknessSeverity(index, weakness) {
  if (weakness?.severity) {
    const value = String(weakness.severity).toLowerCase();
    if (value.includes("high")) return "🔴";
    if (value.includes("medium")) return "🟡";
    return "🟢";
  }
  if (index === 0) return "🔴";
  if (index === 1) return "🟡";
  return "🟢";
}

export default function GapAnalysis({ data }) {
  const meta = scoreInfo(data || {});
  const strengths = data?.strengths || [];
  const weaknesses = data?.weaknesses || [];

  return (
    <div className="mt-6 space-y-4">
      <Card className="rounded-xl p-6">
        <p className="text-sm text-brand-muted">Brand Rating</p>
        <div className="mt-2 flex flex-wrap items-end gap-4">
          <p className="gradient-text text-6xl font-extrabold">{meta.score || 0}</p>
          <span className="pb-2 text-slate-400">/10</span>
          <span className={`mb-2 rounded-full px-3 py-1 text-xs font-bold ${meta.className}`}>
            {meta.badge}
          </span>
        </div>
        <p className="mt-3 text-sm text-slate-300">Snapshot of how your current strategy performs against your niche.</p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="rounded-xl p-6">
          <h3 className="text-lg font-bold">💪 Strengths</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-200">
            {strengths.map((item, idx) => (
              <li key={`s-${idx}`}>🟢 {typeof item === "string" ? item : item?.point || JSON.stringify(item)}</li>
            ))}
          </ul>
        </Card>

        <Card className="rounded-xl p-6">
          <h3 className="text-lg font-bold">⚠️ Weaknesses</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-200">
            {weaknesses.map((item, idx) => (
              <li key={`w-${idx}`}>
                {weaknessSeverity(idx, item)} {typeof item === "string" ? item : item?.point || JSON.stringify(item)}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="rounded-xl p-6">
        <h3 className="text-lg font-bold">🏆 Competitor Advantages</h3>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-200">
          {(data?.competitor_advantages || []).map((item, idx) => (
            <li key={`ca-${idx}`}>{typeof item === "string" ? item : item?.point || JSON.stringify(item)}</li>
          ))}
        </ul>
      </Card>

      <Card className="rounded-xl p-6">
        <h3 className="text-lg font-bold">⚡ Quick Wins</h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {(data?.quick_wins || []).map((item, idx) => (
            <span key={`qw-${idx}`} className="rounded-md border border-green-500/30 bg-green-500/10 px-2.5 py-1 text-xs text-green-200">
              {typeof item === "string" ? item : item?.point || JSON.stringify(item)}
            </span>
          ))}
        </div>
      </Card>

      <Card className="rounded-xl p-6">
        <h3 className="text-lg font-bold">🌐 Market Opportunities</h3>
        {Array.isArray(data?.market_opportunities) ? (
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-200">
            {data.market_opportunities.map((item, idx) => (
              <li key={`mo-${idx}`}>{typeof item === "string" ? item : item?.point || JSON.stringify(item)}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-slate-200">{String(data?.market_opportunities || "No opportunities available")}</p>
        )}
      </Card>
    </div>
  );
}
