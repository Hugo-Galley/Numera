import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true,
    port: 5173,
    allowedHosts: "all",
    // Même URL qu'en prod (/mcp via Nginx) pour le serveur MCP local
    proxy: {
      "/mcp": process.env.MCP_PROXY_TARGET ?? "http://localhost:8100",
    },
  }
})