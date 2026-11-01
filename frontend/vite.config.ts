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
  build: {
    rollupOptions: {
      output: {
        // Les bibliothèques changent rarement : des fichiers séparés gardent leur hash (donc le cache navigateur)
        // d'une version de l'application à l'autre, au lieu d'être renvoyés avec chaque mise à jour du code.
        manualChunks(id) {
          // Aides d'interopérabilité CommonJS de Vite : partagées par tous, elles ne doivent pas tomber dans le chunk des graphiques
          if (id.includes("commonjsHelpers")) return "vendor-react"
          if (!id.includes("node_modules")) return undefined
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "vendor-react"
          if (/node_modules\/(react-router|react-router-dom|@remix-run)\//.test(id)) return "vendor-router"
          if (/node_modules\/(@radix-ui|@floating-ui|aria-hidden|react-remove-scroll[^/]*|react-style-singleton|use-callback-ref|use-sidecar|get-nonce)\//.test(id)) return "vendor-radix"
          if (/node_modules\/(recharts|recharts-scale)\//.test(id)) return "vendor-charts"
          if (/node_modules\/date-fns\//.test(id)) return "vendor-date"
          // Utilitaires partagés par l'application et par les graphiques : hors du chunk des graphiques (sinon chargé dès l'entrée)
          if (/node_modules\/(clsx|tailwind-merge|class-variance-authority)\//.test(id)) return "vendor-ui"
          return undefined
        },
      },
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