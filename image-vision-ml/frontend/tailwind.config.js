/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#071018",
          900: "#0b1620",
          800: "#122230",
          700: "#1a3144",
          600: "#27445c",
        },
        moss: {
          400: "#7dce9a",
          500: "#4fb87a",
          600: "#2f8f58",
        },
        sand: {
          300: "#e4d2a8",
          400: "#d2b57a",
        },
        rust: {
          400: "#e08a5a",
          500: "#c96a3c",
        },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
