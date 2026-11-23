export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Plus Jakarta Sans", "ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Cascadia Code", "Consolas", "monospace"],
      },
      colors: {
        bg: "#F2EBE1",
        ink: "#2F2923",
        ink2: "#5B5249",
        muted: "#8C8176",
        line: "rgba(95, 70, 45, 0.11)",
        surface: "#F9F4EC",
        panel: "#EEE6DA",
        sand: "#E6DCCD",
        brand: { 50: "#E7E4F1", 100: "#D3CFEC", 500: "#4757CF", 600: "#3B49B8", 700: "#2F3A96" },
        pos: "#3F8660", neg: "#B9503F", neu: "#AD6F2B",
        possoft: "#E2ECDC", negsoft: "#F6E0D6", neusoft: "#F5E6CF",
      },
      borderRadius: { xl2: "22px" },
      boxShadow: {
        card: "0 1px 1px rgba(90,60,30,.04), 0 18px 40px -16px rgba(110,75,40,.2)",
        soft: "0 1px 1px rgba(90,60,30,.04), 0 8px 20px -10px rgba(110,75,40,.16)",
        accent: "0 10px 22px -10px rgba(71,87,207,.55)",
      },
    },
  },
  plugins: [],
};
