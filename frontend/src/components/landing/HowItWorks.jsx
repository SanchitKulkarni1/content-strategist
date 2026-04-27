const steps = ["Enter Links", "AI Analysis", "Get Results"];

export default function HowItWorks() {
  return (
    <section className="mx-auto mt-12 max-w-4xl px-6 text-center">
      <h2 className="text-2xl font-bold text-white">How It Works</h2>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3 md:gap-6">
        {steps.map((step, idx) => (
          <div key={step} className="flex items-center gap-3 md:gap-6">
            <div className="text-center">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-r from-blue-500 to-violet-500 text-sm font-bold text-white">
                {idx + 1}
              </div>
              <p className="mt-2 text-sm font-semibold text-slate-200">{step}</p>
            </div>
            {idx < steps.length - 1 ? <span className="text-2xl text-brand-muted">→</span> : null}
          </div>
        ))}
      </div>
    </section>
  );
}
