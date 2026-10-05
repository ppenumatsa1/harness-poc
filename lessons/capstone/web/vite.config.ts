import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The browser only talks to Vite; Vite forwards /api to the api container (SSE streams through).
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: { "/api": { target: process.env.API_URL ?? "http://localhost:8000", changeOrigin: true } },
  },
});
