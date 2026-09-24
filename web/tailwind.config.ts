import type { Config } from "tailwindcss";

// Verification teal theme — values copied verbatim from frontend/.streamlit/config.toml
const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "accent-teal": "#2DD4BF", // primaryColor
        "bg-base": "#0F172A", // backgroundColor
        "bg-surface": "#1E293B", // secondaryBackgroundColor
        "text-primary": "#E2E8F0", // textColor
      },
      borderRadius: {
        lg: "0.75rem",
        md: "0.5rem",
        sm: "0.375rem",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
