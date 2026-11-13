import { test, expect } from "./fixtures"

test.describe("navigation du bureau (sidebar)", () => {
  test("la sidebar mène à chaque section de l'application", async ({ page }) => {
    await page.goto("/")
    const nav = page.getByRole("navigation")
    for (const [label, url] of [
      ["Comptes", /\/accounts$/], ["Épargne", /\/savings$/], ["Investissements", /\/investments$/], ["Fiscalité", /\/tax$/],
      ["Échéances", /\/recurring/], ["Remboursements", /\/reimbursements$/], ["Classement", /\/classement/], ["Simulateur", /\/tools$/],
      ["Centre d'actions", /\/audit$/], ["Bilan annuel", /\/wrapped$/], ["Mois", /\/month/], ["Tableau de bord", /\/$/],
    ] as const) {
      await nav.getByRole("link", { name: new RegExp(`^${label}`) }).click()
      await expect(page).toHaveURL(url)
    }
  })

  test("une adresse inconnue affiche la page introuvable avec retour au tableau de bord", async ({ page }) => {
    await page.goto("/cette-page-nexiste-pas")
    await expect(page.getByText("Page introuvable")).toBeVisible()
    await page.getByRole("link", { name: /Retour au tableau de bord/ }).click()
    await expect(page).toHaveURL(/\/$/)
  })

  test("les anciennes adresses sont redirigées", async ({ page }) => {
    await page.goto("/report")
    await expect(page).toHaveURL(/\/month\/bilan/)
    await page.goto("/calendar")
    await expect(page).toHaveURL(/\/recurring\?tab=calendar/)
  })
})

test.describe("mobile (iPhone SE, 375 px)", () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test("aucune page principale ne déborde horizontalement", async ({ page }) => {
    for (const route of ["/", "/accounts", "/accounts/1", "/savings", "/recurring", "/classement", "/settings"]) {
      await page.goto(route)
      await expect(page.getByRole("heading").first()).toBeVisible()
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
      expect(overflow, `débordement horizontal sur ${route}`).toBeLessThanOrEqual(1)
    }
  })

  test("la liste des opérations s'affiche en cartes et la saisie reste utilisable", async ({ page }) => {
    await page.goto("/accounts/1")
    await expect(page.getByRole("table").first()).toBeHidden()
    await page.getByRole("button", { name: "Nouvelle opération" }).click()
    await expect(page.getByRole("dialog", { name: "Nouvelle opération" })).toBeVisible()
    await page.keyboard.press("Escape")
  })
})
