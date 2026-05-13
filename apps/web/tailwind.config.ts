import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        surface: "var(--surface)",
        "surface-strong": "var(--surface-strong)",
        "surface-ink": "var(--surface-ink)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        accent: "var(--accent)",
        "accent-strong": "var(--accent-strong)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        muted: "var(--muted)",
      },
      fontFamily: {
        sans: ["Geist", "Geist Fallback", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "Geist Mono Fallback", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
