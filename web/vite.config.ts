import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: the Vite origin proxies API calls to FastAPI. Production: FastAPI serves web/dist on one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false }, "/health": "http://127.0.0.1:8000" },
  },
});
