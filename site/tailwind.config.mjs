/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0E14",
        panel: {
          DEFAULT: "#0E1219",
          raised: "#11161F",
        },
        border: "#1E2733",
        accent: {
          cyan: "#22D3EE",
          green: "#34D399",
          amber: "#FBBF24",
          red: "#F87171",
          indigo: "#818CF8",
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Noto Sans SC"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
    },
  },
  plugins: [],
};