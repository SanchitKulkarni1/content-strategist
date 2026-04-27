export default function TrendPill({ trend, active, onClick, loading = false }) {
  return (
    <button
      type="button"
      disabled={loading}
      onClick={() => onClick(trend)}
      className={[
        "rounded-full border px-3.5 py-1.5 text-sm transition disabled:cursor-not-allowed disabled:opacity-70",
        active
          ? "scale-[1.02] border-transparent bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500 text-white"
          : "border-slate-700 bg-slate-800 text-slate-300 hover:border-blue-500",
      ].join(" ")}
    >
      {loading ? "Regenerating..." : trend}
    </button>
  );
}
