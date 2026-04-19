import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        bg: {
          DEFAULT: "#0a0a0f",
          raised: "#12121a",
          card: "#16161f",
          hover: "#1b1b26",
        },
        line: "#26262f",
        ink: {
          DEFAULT: "#e8e8ee",
          muted: "#9a9aab",
          faint: "#60606e",
        },
        accent: {
          DEFAULT: "#10b981",
          soft: "rgba(16,185,129,0.14)",
        },
        danger: "#ef4444",
        warn: "#f59e0b",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(16,185,129,0.25), 0 8px 30px rgba(16,185,129,0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
