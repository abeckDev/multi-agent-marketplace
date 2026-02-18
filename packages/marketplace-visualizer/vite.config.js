import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";
import { defineConfig } from "vite";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // Build configuration - output to magentic-marketplace package
  build: {
    outDir: path.resolve(__dirname, "../magentic-marketplace/src/magentic_marketplace/ui/static"),
    emptyOutDir: true,
  },

  // Dev server configuration - proxy API calls to backend server
  // For unified server: use http://localhost:8000
  // For legacy UI server: use http://localhost:5000
  server: {
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
