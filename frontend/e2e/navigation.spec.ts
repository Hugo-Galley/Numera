import { test, expect } from "@playwright/test"

// Toutes les routes de l'application : aucune page blanche, aucun 404 applicatif, aucune erreur JS ni réponse 5xx.
const ROUTES = [
  "/", "/accounts", "/savings", "/investments", "/month", "/month/bilan", "/month/revue", "/month/comparaison",
  "/recurring", "/reimbursements", "/wrapped", "/audit", "/tools", "/tax", "/classement", "/settings",
]

for (const route of ROUTES) {
  test(`la page ${route} se charge sans erreur`, async ({ page }) => {
    const errors: string[] = []
    page.on("pageerror", (e) => errors.push(`exception : ${e.message}`))
    page.on("console", (m) => m.type() === "error" && errors.push(`console : ${m.text()}`))
    page.on("response", (r) => r.status() >= 500 && errors.push(`HTTP ${r.status()} : ${r.url()}`))

    await page.goto(route)
    await expect(page.getByRole("heading").first()).toBeVisible()
    await expect(page.getByText("Page introuvable")).toHaveCount(0)
    await page.waitForLoadState("networkidle")

    expect(errors).toEqual([])
  })
}
