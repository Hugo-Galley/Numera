import { defineConfig, devices } from "@playwright/test"

// Pile complète en local : backend (base de démo jetable, port 8101) + Vite (port 5174).
// Ports distincts du dev (8001 / 5173) pour pouvoir lancer les E2E pendant qu'un `make dev` tourne.
const API = "http://localhost:8101"
const APP = "http://localhost:5174"

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1, // une seule base partagée : les scénarios qui écrivent ne se marchent pas dessus
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
      testIgnore: /auth\.setup\.ts/,
      dependencies: ["setup"],
      use: { ...devices["Desktop Chrome"], storageState: "e2e/.auth/state.json" },
    },
  ],
  webServer: [
    { command: "sh e2e/backend.sh", url: `${API}/health`, timeout: 120_000, reuseExistingServer: false },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      url: APP,
      timeout: 120_000,
      reuseExistingServer: false,
      env: { VITE_API_BASE: API },
    },
  ],
})
