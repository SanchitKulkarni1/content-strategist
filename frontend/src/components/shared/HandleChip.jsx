function extractHandle(url = "") {
  const normalized = url.trim().replace(/\/$/, "");
  if (!normalized) return "";

  const match = normalized.match(/instagram\.com\/([^/?#]+)/i);
  if (match) return `@${match[1].replace(/^@/, "").toLowerCase()}`;

  return `@${normalized.split("/").pop().replace(/^@/, "").toLowerCase()}`;
}

export default function HandleChip({ url, isBrand = false }) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold",
        isBrand
          ? "border-blue-500/40 bg-blue-500/20 text-blue-300"
          : "border-slate-600 bg-slate-700 text-slate-300",
      ].join(" ")}
    >
      {extractHandle(url)}
    </span>
  );
}
