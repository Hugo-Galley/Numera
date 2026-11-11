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
        // Seuils à cliquet, relevés le 2026-11-11 sur la mesure (933 tests) : 80,11 % instructions,
        // 66,09 % branches, 73,08 % fonctions, 81,84 % lignes, arrondis vers le bas. Ne jamais les baisser ;
        // les relever après chaque lot de tests. (Vitest 4 compte plus de branches et de fonctions que Vitest 3.)
        thresholds: { statements: 80, lines: 81, branches: 66, functions: 73 },
      },
    },
  }),
)
