import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#EEF2FF",
          100: "#E0E7FF",
          600: "#4F46E5",
          700: "#4338CA",
        },
        ink: {
          300: "#CBD5E1",
          500: "#64748B",
          600: "#475569",
          700: "#334155",
          900: "#0F172A",
        },
        surface: "#FFFFFF",
        canvas: "#F8FAFC",
        success: {
          50: "#ECFDF5",
          600: "#059669",
          700: "#047857",
        },
        warning: {
          50: "#FFFBEB",
          600: "#D97706",
          700: "#B45309",
        },
        danger: {
          50: "#FEF2F2",
          600: "#DC2626",
          700: "#B91C1C",
        },
        ai: {
          50: "#F5F3FF",
          600: "#7C3AED",
          700: "#6D28D9",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;

