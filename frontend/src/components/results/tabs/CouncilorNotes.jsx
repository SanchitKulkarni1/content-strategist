import Card from "../../shared/Card";

function toBulletList(value) {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    return value
      .split(/\n|\.\s+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (value && typeof value === "object") {
    return Object.entries(value).map(([key, item]) => `${key}: ${JSON.stringify(item)}`);
  }
  return [];
}

function titleCase(input) {
  return input
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function CouncilorNotes({ data }) {
  const normalized = data && typeof data === "object" ? data : { notes: data };

  return (
    <div className="mt-6">
      <Card className="rounded-xl p-6">
        <p className="text-sm text-brand-muted">
          These are the raw model deliberations from the AI council used to generate your strategy.
        </p>

        <div className="mt-4 space-y-3">
          {Object.entries(normalized).map(([name, content]) => (
            <details key={name} className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
              <summary className="cursor-pointer list-none text-sm font-semibold text-white">
                {titleCase(name)}
              </summary>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-200">
                {toBulletList(content).map((point, idx) => (
                  <li key={`${name}-${idx}`}>{point}</li>
                ))}
              </ul>
            </details>
          ))}
        </div>
      </Card>
    </div>
  );
}
