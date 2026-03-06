import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "#0e1218",
        sidebar: "#0c1016",
        surface: "#12171f",
        surfaceMuted: "#0f131a",
        topBar: "#0c1018",
        accent: "#F97316",
        accentSoft: "#FDBA74",
        agentCyan: "#22d3ee",
        danger: "#EF4444",
        success: "#22C55E",
        warning: "#FACC15",
        textPrimary: "#e5e5e5",
        textMuted: "#737373",
      },
      boxShadow: {
        card: "0 10px 40px rgba(0,0,0,0.6)"
      },
      borderRadius: {
        xl: "0.75rem",
        lg: "0.5rem",
        md: "0.375rem",
      },
      fontFamily: {
        sans: ["system-ui", "ui-sans-serif", "SF Pro Text", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
      }
    },
  },
  plugins: [],
};

export default config;

