export default function TrendPill({ trend, active, onClick }) {
  return (
    <button
      type="button"
      onClick={() => onClick(trend)}
      className={[
        "rounded-full border px-3.5 py-1.5 text-sm transition",
        active
          ? "scale-[1.02] border-transparent bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500 text-white"
          : "border-slate-700 bg-slate-800 text-slate-300 hover:border-blue-500",
      ].join(" ")}
    >
      {trend}
    </button>
  );
}
