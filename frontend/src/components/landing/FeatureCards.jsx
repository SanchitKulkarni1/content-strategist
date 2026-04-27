const cards = [
  {
    icon: "📊",
    title: "Competitive Snapshot",
    description: "Deep-dive metrics on your brand vs competitors",
  },
  {
    icon: "🔍",
    title: "Trend-Aware Planning",
    description: "SERP + Google Trends data woven into every recommendation",
  },
  {
    icon: "📝",
    title: "Ready-To-Post Briefs",
    description: "Shoot-ready content with hooks, captions, and CTAs",
  },
];

export default function FeatureCards() {
  return (
    <section className="mx-auto mt-10 grid w-full max-w-5xl gap-6 px-6 md:grid-cols-3">
      {cards.map((card) => (
        <article
          key={card.title}
          className="glass-card rounded-2xl border border-brand-border p-7 transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_20px_40px_rgba(59,130,246,0.15)]"
        >
          <div className="text-3xl">{card.icon}</div>
          <h3 className="mt-3 text-lg font-bold text-white">{card.title}</h3>
          <p className="mt-2 text-sm text-brand-muted">{card.description}</p>
        </article>
      ))}
    </section>
  );
}
