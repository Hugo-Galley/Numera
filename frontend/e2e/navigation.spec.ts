import { test, expect } from "./fixtures"

// Toutes les routes de l'application : aucune page blanche, aucun 404 applicatif, aucune erreur JS ni réponse 5xx.
const ROUTES = [
  "/", "/accounts", "/savings", "/investments", "/month", "/month/bilan", "/month/revue", "/month/comparaison",
  "/recurring", "/reimbursements", "/wrapped", "/audit", "/tools", "/tax", "/classement", "/settings",
]

for (const route of ROUTES) {
  test(`la page ${route} se charge sans erreur (garde console / 5xx de la fixture)`, async ({ page }) => {
    await page.goto(route)
    await expect(page.getByRole("heading").first()).toBeVisible()
    await expect(page.getByText("Page introuvable")).toHaveCount(0)
    await page.waitForLoadState("networkidle")
  })
}
