export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Nunito", "system-ui", "Segoe UI", "sans-serif"], mono: ["Consolas", "ui-monospace", "monospace"] },
      colors: {
        ink: "#2E2A27", muted: "#7A716A", line: "#EADFD1", surface: "#F8F2EA", panel: "#FBF7F1", sand: "#EFE5D8",
        brand: { 50: "#FBEFE9", 100: "#F4DCD2", 500: "#C8573F", 600: "#AF4934", 700: "#3D5753" },
        pos: "#0F8C74", neg: "#D0533C", neu: "#D9A136",
      },
      boxShadow: { card: "0 1px 2px rgba(61,45,30,.05), 0 2px 6px rgba(61,45,30,.05)" },
    },
  },
  plugins: [],
};
