import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: the Vite origin proxies API calls to FastAPI. Production: FastAPI serves web/dist on one origin.
declare const process: { env: Record<string, string | undefined> };
const API = `http://127.0.0.1:${process.env.API_PORT ?? 8000}`;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: API, changeOrigin: false }, "/health": API },
  },
});
