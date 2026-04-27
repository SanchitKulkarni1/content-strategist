import { useEffect, useState } from "react";

export default function SuccessBanner({ dismissed, onDismiss }) {
  const [isClosing, setIsClosing] = useState(false);

  useEffect(() => {
    setIsClosing(false);
  }, [dismissed]);

  if (dismissed) {
    return null;
  }

  return (
    <div className={`slide-down ${isClosing ? "slide-up" : ""} rounded-xl border border-green-500/30 bg-green-500/10 p-4 text-green-400`}>
      <div className="flex items-start justify-between gap-3">
        <p>✅ Analysis Complete — your strategy is ready.</p>
        <button
          type="button"
          className="text-green-300 hover:text-green-100"
          onClick={() => {
            setIsClosing(true);
            setTimeout(() => onDismiss(), 170);
          }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
