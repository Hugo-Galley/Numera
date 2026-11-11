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
        // Seuils à cliquet, relevés le 2026-11-11 sur la mesure complète (976 tests) : 75,99 % instructions,
        // 63,55 % branches, 68,1 % fonctions, 77,5 % lignes, arrondis vers le bas. Un fichier jamais chargé par un
        // test est compté à 0 instruction par v8 : toute page ou tout composant nouveau doit venir avec un test
        // qui le charge, sinon la mesure est surévaluée. Ne jamais les baisser ; les relever après chaque lot de tests.
        thresholds: { statements: 75, lines: 77, branches: 63, functions: 68 },
      },
    },
  }),
)
