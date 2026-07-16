import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.FRONTEND_PORT) || 5173,
    proxy: {
      "/health": "http://localhost:8000",
      "/videos": "http://localhost:8000",
      "/intake": "http://localhost:8000",
    },
  },
});
