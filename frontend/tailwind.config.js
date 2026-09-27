/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1a1f2b",
        panel: "#f5f6f8",
      },
    },
  },
  plugins: [],
};
