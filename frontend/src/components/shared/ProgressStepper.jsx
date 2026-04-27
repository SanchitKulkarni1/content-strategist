const STEP_ORDER = ["scraping", "trends", "analyzing", "generating", "complete"];
const STEP_LABELS = {
  scraping: "Scraping",
  trends: "Trends",
  analyzing: "Analyzing",
  generating: "Generating",
  complete: "Complete",
};

function estimateMinutes(percent) {
  if (!percent || percent >= 100) return "<1";
  const remaining = Math.max(0, 100 - percent);
  return String(Math.max(1, Math.ceil((remaining / 100) * 5)));
}

export default function ProgressStepper({ progress }) {
  const currentIndex = Math.max(0, STEP_ORDER.indexOf(progress.stage));

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-5xl">
        <h2 className="gradient-text text-center text-4xl font-extrabold">
          Analyzing your content strategy...
        </h2>
        <p className="mt-2 text-center text-brand-muted">{progress.message}</p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-5 md:gap-7">
          {STEP_ORDER.map((step, idx) => {
            const completed = idx < currentIndex;
            const active = idx === currentIndex;
            return (
              <div key={step} className="flex items-center gap-4">
                <div className="text-center">
                  <div
                    className={[
                      "mx-auto flex h-11 w-11 items-center justify-center rounded-full text-sm font-bold",
                      completed && "bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500 text-white",
                      active && !completed && "pulse-ring border border-blue-400 bg-slate-700 text-white",
                      !active && !completed && "bg-slate-700 text-slate-400",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    {completed ? "✓" : idx + 1}
                  </div>
                  <p className="mt-2 text-sm text-slate-300">{STEP_LABELS[step]}</p>
                </div>
                {idx < STEP_ORDER.length - 1 ? <span className="text-slate-500">→</span> : null}
              </div>
            );
          })}
        </div>

        <div className="mx-auto mt-10 h-2.5 w-full max-w-3xl overflow-hidden rounded-full bg-slate-700">
          <div
            className="h-full rounded-full bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500 transition-all duration-500"
            style={{ width: `${Math.min(100, Math.max(0, progress.percent || 0))}%` }}
          />
        </div>

        <p className="mt-3 text-center text-sm text-slate-400">
          ~{estimateMinutes(progress.percent)} min remaining
        </p>
      </div>
    </div>
  );
}
