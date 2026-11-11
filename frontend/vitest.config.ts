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
      setupFiles: ["src/test/support/setup.ts"],
      env: { TZ: "Europe/Paris" },
      css: false,
      restoreMocks: true,
      include: ["src/test/**/*.test.{ts,tsx}"],
      // Node ≥ 25 expose son propre localStorage (vide sans --localstorage-file), qui masque celui de jsdom
      execArgv: ["--no-experimental-webstorage"],
      coverage: {
        provider: "v8",
        include: ["src/**/*.{ts,tsx}"],
        exclude: ["src/test/**", "src/components/ui/**", "src/**/*.d.ts"],
        // Seuils à cliquet, recalés le 2026-11-04 au passage à Vitest 4 : sa couverture v8 (remappage AST)
        // compte plus de branches et de fonctions qu'avant (même suite de tests, 606 tests), d'où des
        // pourcentages non comparables à l'ancienne mesure (40/72/56/40). Niveau mesuré : 45,14 % instructions,
        // 34,72 % branches, 37,77 % fonctions, 45,4 % lignes, arrondi vers le bas. Ne jamais les baisser.
        thresholds: { statements: 45, lines: 45, branches: 34, functions: 37 },
      },
    },
  }),
)
