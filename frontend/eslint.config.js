import js from "@eslint/js"
import globals from "globals"
import reactHooks from "eslint-plugin-react-hooks"
import tseslint from "typescript-eslint"

// Config minimale : erreurs de logique et hooks React, pas de règle de style (pas de formateur imposé).
// Les écarts existants sont plafonnés par fichier dans eslint-baseline.json (cf. scripts/check-lint.mjs).
export default tseslint.config(
  { ignores: ["dist", "coverage", "playwright-report", "test-results", "src/components/ui/**", "src/lib/api/generated/**"] },
  {
    files: ["src/**/*.{ts,tsx}", "e2e/**/*.ts", "*.ts", "*.js"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "no-unused-vars": "off",
      // `any` omniprésent (réponses d'API, mocks de test) : le typage strict se fait via tsc, pas ici
      "@typescript-eslint/no-explicit-any": "off",
      // espaces insécables fines dans les regex de montants français : voulu
      "no-irregular-whitespace": ["error", { skipRegExps: true }],
    },
  },
)
