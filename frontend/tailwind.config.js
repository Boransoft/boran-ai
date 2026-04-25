/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        shell: "#0b1020",
        card: "#121a30",
        accent: "#17c3b2",
        muted: "#8ea3c0",
      },
      boxShadow: {
        soft: "0 8px 30px rgba(5,10,25,0.28)",
      },
    },
  },
  plugins: [],
};
