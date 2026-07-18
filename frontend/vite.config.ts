import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend runs on :8000 (uvicorn app.main:app). Proxy API calls in dev so the frontend
// can call /studies, /runs, ... without CORS config.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/studies": "http://localhost:8000",
      "/runs": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
