import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // HotLead design system — Data-Dense Dashboard
        background: "#020617",
        surface: {
          DEFAULT: "#0F172A",
          elevated: "#1E293B",
        },
        brand: {
          DEFAULT: "#22C55E",
          hover: "#16A34A",
          muted: "#166534",
        },
        text: {
          DEFAULT: "#F8FAFC",
          secondary: "#94A3B8",
          muted: "#475569",
        },
        border: {
          DEFAULT: "#1E293B",
          subtle: "#0F172A",
        },
        status: {
          pending:  "#64748B",
          running:  "#22C55E",
          paused:   "#F59E0B",
          done:     "#3B82F6",
          error:    "#EF4444",
        },
      },
      fontFamily: {
        mono: ["Fira Code", "monospace"],
        sans: ["Fira Sans", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
