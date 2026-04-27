import Card from "../../shared/Card";

function toList(value) {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") return [value];
  return [];
}

const sections = [
  { key: "executive_summary", title: "📌 Executive Summary" },
  { key: "top_3_fixes", title: "🔧 Top 3 Fixes" },
  { key: "double_down_on", title: "🚀 Double Down On" },
  { key: "30_day_plan", title: "📅 30-Day Plan" },
];

export default function StrategicReport({ data }) {
  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-2">
      {sections.map((section) => {
        const value = data?.[section.key] ?? "";
        const list = toList(value);

        return (
          <Card key={section.key} className="rounded-xl p-6">
            <h3 className="inline-block border-b-2 border-blue-500 pb-1 text-lg font-bold text-white">
              {section.title}
            </h3>

            {list.length > 1 ? (
              <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-200">
                {list.map((item, idx) => (
                  <li key={`${section.key}-${idx}`}>{item}</li>
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
