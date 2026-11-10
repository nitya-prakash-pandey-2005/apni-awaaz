import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { cpSync } from "node:fs";
import { fileURLToPath } from "node:url";

const voiceWeb = fileURLToPath(new URL("../voice-core/web", import.meta.url));
const demoData = fileURLToPath(new URL("./demo", import.meta.url));
const sharedData = fileURLToPath(new URL("../backend/awaaz/data", import.meta.url)); // templates shared with the backend

// `vite build --mode demo` (npm run build:demo) also copies the recorded session in demo/ to dist/demo/.
// The normal build is unchanged and ships no demo files.
const demoFiles = (mode) => ({
  name: "awaaz-demo-files",
  apply: "build",
  closeBundle() {
    if (mode === "demo") cpSync(demoData, fileURLToPath(new URL("./dist/demo", import.meta.url)), { recursive: true });
  },
});

export default defineConfig(({ mode }) => ({
  plugins: [react(), demoFiles(mode)],
  resolve: { alias: { "@voice": voiceWeb, "@data": sharedData } },
  server: {
    port: 5193,
    fs: { allow: [".", voiceWeb, sharedData] },
    proxy: {
      "/api": "http://127.0.0.1:8767",
      "/ws": { target: "ws://127.0.0.1:8767", ws: true },
    },
  },
  build: { target: "es2022" },
}));
