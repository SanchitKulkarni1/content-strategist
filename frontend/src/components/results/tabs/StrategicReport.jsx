import Card from "../../shared/Card";

function toList(value) {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") return [value];
  return [];
}

function renderInlineBold(text) {
  const parts = String(text || "").split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, idx) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      return <strong key={`b-${idx}`}>{part.slice(2, -2)}</strong>;
    }
    return <span key={`t-${idx}`}>{part}</span>;
  });
}

function parsePipeTable(lines, keyPrefix) {
  const rows = lines
    .map((line) =>
      line
        .trim()
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((cell) => cell.trim())
    )
    .filter((cells) => cells.length > 0);

  if (rows.length === 0) return null;

  const isDivider = (cells) => cells.every((cell) => /^:?-{3,}:?$/.test(cell));
  const hasHeaderDivider = rows.length > 1 && isDivider(rows[1]);
  const header = hasHeaderDivider ? rows[0] : null;
  const body = hasHeaderDivider ? rows.slice(2) : rows;

  if (body.length === 0) return null;

  return (
    <div key={`${keyPrefix}-table-wrap`} className="mt-4 overflow-x-auto">
      <table className="min-w-full border-collapse text-left text-sm text-slate-200">
        {header ? (
          <thead>
            <tr>
              {header.map((cell, idx) => (
                <th key={`${keyPrefix}-h-${idx}`} className="border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300">
                  {renderInlineBold(cell)}
                </th>
              ))}
            </tr>
          </thead>
        ) : null}
        <tbody>
          {body.map((cells, rowIdx) => (
            <tr key={`${keyPrefix}-r-${rowIdx}`}>
              {cells.map((cell, colIdx) => (
                <td key={`${keyPrefix}-c-${rowIdx}-${colIdx}`} className="border border-slate-700 px-3 py-2 align-top">
                  {renderInlineBold(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function parseMarkdownBlocks(text, keyPrefix) {
  const lines = String(text || "").split(/\r?\n/);
  const nodes = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    const headingMatch = trimmed.match(/^##\s+(.+)$/);
    if (headingMatch) {
      nodes.push(
        <h4 key={`${keyPrefix}-h-${i}`} className="mt-4 text-base font-semibold text-white first:mt-0">
          {renderInlineBold(headingMatch[1])}
        </h4>
      );
      i += 1;
      continue;
    }

    if (/^\|.*\|$/.test(trimmed)) {
      const tableLines = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
        tableLines.push(lines[i]);
        i += 1;
      }
      const tableNode = parsePipeTable(tableLines, `${keyPrefix}-${i}`);
      if (tableNode) nodes.push(tableNode);
      continue;
    }

    const paragraph = [trimmed];
    i += 1;
    while (i < lines.length) {
      const lookAhead = lines[i].trim();
      if (!lookAhead || /^##\s+/.test(lookAhead) || /^\|.*\|$/.test(lookAhead)) break;
      paragraph.push(lookAhead);
      i += 1;
    }

    nodes.push(
      <p key={`${keyPrefix}-p-${i}`} className="mt-3 text-sm leading-relaxed text-slate-200 first:mt-0">
        {renderInlineBold(paragraph.join(" "))}
      </p>
    );
  }

  return nodes;
}

function splitLegacySections(text) {
  const raw = String(text || "");
  const sectionRegex = /(?:^|\n)\s*(?:##\s*)?(EXECUTIVE SUMMARY|TOP 3 THINGS TO FIX IMMEDIATELY|TOP 3 THINGS TO DOUBLE DOWN ON|30-DAY ACTION PLAN(?: \(week-by-week\))?)\s*:?\s*(?=\n|$)/gi;
  const matches = [...raw.matchAll(sectionRegex)];
  if (matches.length === 0) {
    return {
      executiveSummary: raw,
      top3Fixes: [],
      doubleDownOn: [],
      thirtyDayPlan: [],
    };
  }

  const sections = {
    executiveSummary: "",
    top3Fixes: [],
    doubleDownOn: [],
    thirtyDayPlan: [],
  };

  const normalize = (name) => {
    const value = name.toUpperCase();
    if (value.includes("EXECUTIVE SUMMARY")) return "executiveSummary";
    if (value.includes("FIX")) return "top3Fixes";
    if (value.includes("DOUBLE DOWN")) return "doubleDownOn";
    return "thirtyDayPlan";
  };

  matches.forEach((match, idx) => {
    const key = normalize(match[1]);
    const start = (match.index || 0) + match[0].length;
    const end = idx + 1 < matches.length ? matches[idx + 1].index : raw.length;
    const chunk = raw.slice(start, end).trim();
    if (!chunk) return;

    if (key === "executiveSummary") {
      sections.executiveSummary = chunk;
      return;
    }

    sections[key] = chunk
      .split(/\r?\n/)
      .map((line) => line.replace(/^[-*\d.)\s]+/, "").trim())
      .filter(Boolean);
  });

  if (!sections.executiveSummary) {
    sections.executiveSummary = raw;
  }

  return sections;
}

function normalizeReport(data) {
  const report = data || {};
  const executiveSummary =
    report.executiveSummary ||
    report.executive_summary ||
    report.summary ||
    "";

  const top3Fixes = toList(report.top3Fixes ?? report.top_3_fixes);
  const doubleDownOn = toList(report.doubleDownOn ?? report.double_down_on);
  const thirtyDayPlan = toList(report.thirtyDayPlan ?? report["30_day_plan"]);

  if (top3Fixes.length || doubleDownOn.length || thirtyDayPlan.length) {
    return { executiveSummary, top3Fixes, doubleDownOn, thirtyDayPlan };
  }

  const legacy = splitLegacySections(executiveSummary);
  return {
    executiveSummary: legacy.executiveSummary,
    top3Fixes: legacy.top3Fixes,
    doubleDownOn: legacy.doubleDownOn,
    thirtyDayPlan: legacy.thirtyDayPlan,
  };
}

const sections = [
  { key: "executiveSummary", title: "📌 Executive Summary", type: "markdown" },
  { key: "top3Fixes", title: "🔧 Top 3 Fixes", type: "list" },
  { key: "doubleDownOn", title: "🚀 Double Down On", type: "list" },
  { key: "thirtyDayPlan", title: "📅 30-Day Plan", type: "list" },
];

export default function StrategicReport({ data }) {
  const normalized = normalizeReport(data);

  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-2">
      {sections.map((section) => {
        const value = normalized?.[section.key] ?? "";
        const list = toList(value);

        return (
          <Card key={section.key} className="rounded-xl p-6">
            <h3 className="inline-block border-b-2 border-blue-500 pb-1 text-lg font-bold text-white">
              {section.title}
            </h3>

            {section.type === "markdown" ? (
              <div className="mt-4">{parseMarkdownBlocks(list[0] || "", section.key)}</div>
            ) : list.length > 0 ? (
              <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-200">
                {list.map((item, idx) => (
                  <li key={`${section.key}-${idx}`}>{parseMarkdownBlocks(item, `${section.key}-${idx}`)}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm leading-relaxed text-slate-200">
                {list[0] || "No data available."}
              </p>
            )}
          </Card>
        );
      })}
    </div>
  );
}
