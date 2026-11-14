import { defineConfig, devices } from "@playwright/test"

// Pile complète en local : backend (base de démo jetable, port 8101) + Vite (port 5174).
// Ports distincts du dev (8001 / 5173) pour pouvoir lancer les E2E pendant qu'un `make dev` tourne.
const API = "http://localhost:8101"
const APP = "http://localhost:5174"
// Profil « security » : pile séparée (backend NON démo sur base jetable, port 8102 / Vite 5175 / faux services 8103)
const SEC_API = "http://localhost:8102"
const SEC_APP = "http://localhost:5175"

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1, // une seule base partagée : les scénarios qui écrivent ne se marchent pas dessus
  // Premier chargement à froid de Vite (optimisation des dépendances) : marge sur les attentes
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: APP,
    locale: "fr-FR",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      testIgnore: [/auth\.setup\.ts/, /security\//],
      dependencies: ["setup"],
      use: { ...devices["Desktop Chrome"], storageState: "e2e/.auth/state.json" },
    },
    // 2FA, passkeys, jetons MCP, sauvegardes, notifications : bloqués en mode démo, donc pile dédiée non démo
    { name: "setup-security", testMatch: /security\/login\.setup\.ts/, use: { baseURL: SEC_APP } },
    {
      name: "security",
      testMatch: /security\/.*\.spec\.ts/,
      dependencies: ["setup-security"],
      use: { ...devices["Desktop Chrome"], baseURL: SEC_APP, storageState: "e2e/.auth/security.json" },
    },
  ],
  webServer: [
    { command: "sh e2e/backend.sh", url: `${API}/health`, timeout: 120_000, reuseExistingServer: !process.env.CI },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      url: APP,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      env: { VITE_API_BASE: API },
    },
    { command: "sh e2e/backend-security.sh", url: `${SEC_API}/health`, timeout: 120_000, reuseExistingServer: !process.env.CI },
    { command: "node e2e/mock-external.mjs", url: "http://127.0.0.1:8103/health", timeout: 30_000, reuseExistingServer: !process.env.CI },
    {
      command: "npm run dev -- --port 5175 --strictPort",
      url: SEC_APP,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      env: { VITE_API_BASE: SEC_API },
    },
  ],
})
