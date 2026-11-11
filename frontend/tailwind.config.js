/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      colors: {
        brand: {
          navy: "#0F172A",
          blue: "#1E3A8A",
          emerald: "#059669",
          amber: "#D97706",
        },
      },
    },
  },
  plugins: [],
};
