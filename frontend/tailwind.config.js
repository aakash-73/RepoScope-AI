/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        charcoal: {
          DEFAULT: "#121212",
          50: "#2a2a2a",
          100: "#1e1e1e",
          200: "#181818",
          300: "#121212",
        },
        moss: {
          DEFAULT: "#B6FF3B",
          dim: "#8fd62a",
          dark: "#5a8a00",
          glow: "rgba(182,255,59,0.15)",
        },
        slate: {
          700: "#374151",
          600: "#4B5563",
          500: "#6B7280",
          400: "#9CA3AF",
        },
        danger: "#FF4500",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
        body: ["'DM Sans'", "sans-serif"],
      },
      boxShadow: {
        moss: "0 0 20px rgba(182,255,59,0.3)",
        "moss-sm": "0 0 8px rgba(182,255,59,0.2)",
        glass: "0 8px 32px rgba(0,0,0,0.5)",
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(rgba(182,255,59,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(182,255,59,0.03) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "40px 40px",
      },
      animation: {
        "pulse-moss": "pulse-moss 2s ease-in-out infinite",
        "slide-in": "slide-in 0.3s ease-out",
        "fade-up": "fade-up 0.4s ease-out",
      },
      keyframes: {
        "pulse-moss": {
          "0%, 100%": { boxShadow: "0 0 8px rgba(182,255,59,0.2)" },
          "50%": { boxShadow: "0 0 20px rgba(182,255,59,0.5)" },
        },
        "slide-in": {
          from: { transform: "translateX(100%)", opacity: 0 },
          to: { transform: "translateX(0)", opacity: 1 },
        },
        "fade-up": {
          from: { transform: "translateY(12px)", opacity: 0 },
          to: { transform: "translateY(0)", opacity: 1 },
        },
      },
    },
  },
  plugins: [],
};
