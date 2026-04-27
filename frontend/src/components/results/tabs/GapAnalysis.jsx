import Card from "../../shared/Card";

function parseItem(item) {
  if (item && typeof item === "object") return item;
  if (typeof item === "string") {
    const raw = item.trim();
    if ((raw.startsWith("{") && raw.endsWith("}")) || (raw.startsWith("[") && raw.endsWith("]"))) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object") return parsed;
      } catch {
        // Keep raw string as fallback content.
      }
    }
    return { area: raw, evidence: "", score: null };
  }
  return { area: String(item || ""), evidence: "", score: null };
}

function normalizeItems(value) {
  if (!Array.isArray(value)) return [];
  return value.map(parseItem);
}

function itemHeading(item) {
  return item.area || item.action || item.opportunity || item.advantage || item.competitor || item.point || "Untitled";
}

function itemBody(item) {
  return item.evidence || item.expected_impact || item.trend_signal || item.how_to_counter || item.advantage || "No supporting detail provided.";
}

function itemBadge(item) {
  if (item.score != null && item.score !== "") {
    return { label: `Score ${item.score}`, className: "bg-blue-500/20 text-blue-200" };
  }
  if (item.impact) {
    return { label: `Impact ${String(item.impact)}`, className: "bg-amber-500/20 text-amber-200" };
  }
  if (item.effort) {
    return { label: `Effort ${String(item.effort)}`, className: "bg-violet-500/20 text-violet-200" };
  }
  if (item.urgency) {
    return { label: `Urgency ${String(item.urgency)}`, className: "bg-emerald-500/20 text-emerald-200" };
  }
  return { label: "Insight", className: "bg-slate-500/20 text-slate-200" };
}

function InsightList({ items, emptyText }) {
  if (items.length === 0) {
    return <p className="mt-3 text-sm text-slate-300">{emptyText}</p>;
  }

  return (
    <div className="mt-3 space-y-3">
      {items.map((rawItem, idx) => {
        const item = parseItem(rawItem);
        const badge = itemBadge(item);

        return (
          <article key={`insight-${idx}`} className="rounded-lg border border-slate-700 bg-slate-900/50 p-3">
            <div className="flex items-start justify-between gap-2">
              <h4 className="text-sm font-semibold text-white">{itemHeading(item)}</h4>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${badge.className}`}>
                {badge.label}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-300">{itemBody(item)}</p>
          </article>
        );
      })}
    </div>
  );
}

function scoreInfo(gap) {
  const raw = gap?.overall_score;
  const score = typeof raw === "number" ? raw : Number(raw?.brand_rating || raw?.score || 0);

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
  const strengths = normalizeItems(data?.strengths);
  const weaknesses = normalizeItems(data?.weaknesses);
  const competitorAdvantages = normalizeItems(data?.competitor_advantages);
  const quickWins = normalizeItems(data?.quick_wins);
  const opportunities = normalizeItems(data?.market_opportunities);

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
          <InsightList items={strengths} emptyText="No strengths available." />
        </Card>

        <Card className="rounded-xl p-6">
          <h3 className="text-lg font-bold">⚠️ Weaknesses</h3>
          <InsightList items={weaknesses.map((item, idx) => ({ ...item, severityIcon: weaknessSeverity(idx, item) }))} emptyText="No weaknesses available." />
        </Card>
      </div>

      <Card className="rounded-xl p-6">
        <h3 className="text-lg font-bold">🏆 Competitor Advantages</h3>
        <InsightList items={competitorAdvantages} emptyText="No competitor advantages available." />
      </Card>

      <Card className="rounded-xl p-6">
        <h3 className="text-lg font-bold">⚡ Quick Wins</h3>
        <InsightList items={quickWins} emptyText="No quick wins available." />
      </Card>

      <Card className="rounded-xl p-6">
        <h3 className="text-lg font-bold">🌐 Market Opportunities</h3>
        <InsightList items={opportunities} emptyText="No opportunities available." />
      </Card>
    </div>
  );
}
