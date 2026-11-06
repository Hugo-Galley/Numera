import path from "node:path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  build: {
    // vendor-charts (recharts + d3 + lodash, ~530 Ko) est chargé à la demande, jamais à l'entrée : seuil relevé au-dessus de lui
    chunkSizeWarningLimit: 600,
    rolldownOptions: {
      output: {
        // Les bibliothèques changent rarement : des fichiers séparés gardent leur hash (donc le cache navigateur)
        // d'une version de l'application à l'autre, au lieu d'être renvoyés avec chaque mise à jour du code.
        codeSplitting: {
          // Seuls les modules qui correspondent au motif entrent dans le groupe : sinon Rolldown y ramène aussi leurs
          // dépendances et le chunk des graphiques, préchargé à l'entrée, avale des modules partagés. Contrepartie : les
          // dépendances de recharts sont listées ci-dessous ; une qui manque tombe dans un chunk de page, d'où un cycle
          // d'import (`TypeError … is not a function` en production uniquement, invisible en dev et dans les tests).
          includeDependenciesRecursively: false,
          groups: [
            { name: "vendor-react", test: /node_modules\/(react|react-dom|scheduler|react-is|prop-types|object-assign)\//, priority: 60 },
            { name: "vendor-router", test: /node_modules\/(react-router|react-router-dom|@remix-run)\//, priority: 50 },
            {
              name: "vendor-radix",
              test: /node_modules\/(@radix-ui|@floating-ui|aria-hidden|react-remove-scroll[^/]*|react-style-singleton|use-callback-ref|use-sidecar|get-nonce)\//,
              priority: 40,
            },
            { name: "vendor-charts", test: /node_modules\/(recharts|recharts-scale|react-smooth|react-transition-group|victory-vendor|d3-[a-z-]+|internmap|lodash|eventemitter3|tiny-invariant|fast-equals|decimal\.js-light)\//, priority: 30 },
            { name: "vendor-date", test: /node_modules\/date-fns\//, priority: 20 },
            // Utilitaires partagés par l'application et par les graphiques : hors du chunk des graphiques (sinon chargé dès l'entrée)
            { name: "vendor-ui", test: /node_modules\/(clsx|tailwind-merge|class-variance-authority)\//, priority: 10 },
          ],
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