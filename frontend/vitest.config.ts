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
        // Seuils à cliquet, relevés le 2026-11-12 sur la mesure complète (1269 tests) : 85,79 % instructions,
        // 71,30 % branches, 79,08 % fonctions, 87,04 % lignes, arrondis vers le bas. Un fichier jamais chargé par un
        // test est compté à 0 instruction par v8 : toute page ou tout composant nouveau doit venir avec un test
        // qui le charge, sinon la mesure est surévaluée. Ne jamais les baisser ; les relever après chaque lot de tests.
        thresholds: { statements: 85, lines: 87, branches: 71, functions: 79 },
      },
    },
  }),
)
