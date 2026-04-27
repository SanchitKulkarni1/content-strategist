const tabs = [
  "📋 Strategic Report",
  "📊 Gap Analysis",
  "📝 Post Prompts",
  "🧠 Councilor Notes",
];

export default function TabNav({ activeTab, onTabChange }) {
  return (
    <nav className="border-b border-slate-800">
      <div className="flex flex-wrap gap-6">
        {tabs.map((tab, idx) => (
          <button
            type="button"
            key={tab}
            onClick={() => onTabChange(idx)}
            className={[
              "relative pb-3 pt-1 text-sm transition",
              activeTab === idx ? "text-white" : "text-brand-muted hover:text-white",
            ].join(" ")}
          >
            {tab}
            {activeTab === idx ? (
              <span className="absolute inset-x-0 -bottom-[1px] h-[3px] rounded-full bg-gradient-to-r from-blue-500 to-violet-500" />
            ) : null}
          </button>
        ))}
      </div>
    </nav>
  );
}
