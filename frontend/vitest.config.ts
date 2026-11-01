import { defineConfig, mergeConfig } from "vitest/config"
import viteConfig from "./vite.config"

// Fixé avant le démarrage des workers : les dates des tests ne dépendent pas de la machine
process.env.TZ = "Europe/Paris"

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["src/test/setup.ts"],
      env: { TZ: "Europe/Paris" },
      css: false,
      restoreMocks: true,
      include: ["src/**/*.test.{ts,tsx}"],
      // Node ≥ 25 expose son propre localStorage (vide sans --localstorage-file), qui masque celui de jsdom
      poolOptions: { forks: { execArgv: ["--no-experimental-webstorage"] } },
      coverage: {
        provider: "v8",
        include: ["src/**/*.{ts,tsx}"],
        exclude: ["src/test/**", "src/**/*.test.{ts,tsx}", "src/components/ui/**", "src/**/*.d.ts"],
        // Seuils à cliquet : niveau mesuré au 2026-11-01 (40,08 % lignes, 72,11 % branches, 56,63 % fonctions),
        // arrondi vers le bas. Ne jamais les baisser ; les relever quand la couverture progresse.
        thresholds: { statements: 40, lines: 40, branches: 72, functions: 56 },
      },
    },
  }),
)
