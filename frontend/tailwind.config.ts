import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Fira Sans"', "system-ui", "sans-serif"],
        mono: ['"Fira Code"', "ui-monospace", "monospace"],
      },
      colors: {
        brand: {
          blue: "#3B82F6",
          orange: "#F97316",
        },
        variant: {
          vibe: "#A855F7",
          automation: "#10B981",
          video: "#EC4899",
        },
      },
      borderRadius: {
        button: "6px",
        card: "8px",
      },
    },
  },
  plugins: [],
};

export default config;
