import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  root: ".",
  base: "./",
  build: {
    outDir: "dist/renderer",
    emptyOutDir: false
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
    css: true,
    exclude: ["tests/e2e/**", "node_modules/**", "dist/**"]
  }
});
