/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: "var(--bg-primary)",
          card: "var(--bg-card)",
          border: "var(--border)",
          text: "var(--text-primary)",
          muted: "var(--text-muted)",
          blue: "var(--accent-blue)",
          purple: "var(--accent-purple)",
          pink: "var(--accent-pink)",
          success: "var(--success)",
          warning: "var(--warning)",
          danger: "var(--danger)"
        }
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "ui-sans-serif", "system-ui"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular"]
      }
    },
  },
  plugins: [],
};
