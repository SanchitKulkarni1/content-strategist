export default function Card({ className = "", children }) {
  return (
    <div
      className={`glass-card rounded-2xl border border-brand-border/90 p-6 ${className}`}
    >
      {children}
    </div>
  );
}
