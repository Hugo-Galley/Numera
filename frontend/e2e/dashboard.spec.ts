import { test, expect } from "./fixtures"

test("tableau de bord : KPI du mois et onglets Aperçu, Budgets, Dépenses", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible()
  for (const kpi of ["Revenus Mensuels", "Dépenses Mensuelles", "Épargne Réalisée"]) {
    await expect(page.getByText(kpi, { exact: true })).toBeVisible()
  }
  for (const tab of ["Budgets", "Dépenses", "Aperçu"]) {
    await page.getByRole("tab", { name: tab }).click()
    await expect(page.getByRole("tab", { name: tab })).toHaveAttribute("aria-selected", "true")
    await expect(page.getByRole("tabpanel", { name: tab }).getByRole("heading").first()).toBeVisible()
  }
})

// BUG CONNU (trouvé par ce scénario) : les graphiques « Flux de trésorerie » (Analyse) et « Évolution du Solde
// Projeté » (Projections) émettent des centaines d'erreurs console « <rect> attribute x/width: NaN ». Le scénario
// est attendu en échec (`test.fail`) : le jour où le bug est corrigé il passe, Playwright le signale et il suffit
// de retirer la ligne `test.fail`.
for (const tab of ["Analyse", "Projections"]) {
  test(`onglet ${tab} sans erreur console`, async ({ page }) => {
    test.fail(true, "NaN dans les attributs <rect> des graphiques Recharts de l'onglet")
    await page.goto("/")
    await page.getByRole("tab", { name: tab }).click()
    await expect(page.getByRole("tabpanel", { name: tab }).getByRole("heading").first()).toBeVisible()
    await page.waitForTimeout(1500) // laisse les graphiques se dessiner (les erreurs arrivent au rendu)
  })
}

test("filtre par compte : l'intitulé du compte remplace « Tous les comptes »", async ({ page }) => {
  await page.goto("/")
  const filter = page.getByRole("combobox").filter({ hasText: "Tous les comptes" })
  await filter.click()
  await page.getByRole("option", { name: "Livret A" }).click()
  await expect(page.getByRole("combobox").filter({ hasText: "Livret A" })).toBeVisible()
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible()
})

test("changement de mois : la période de paie affichée suit la sélection", async ({ page }) => {
  await page.goto("/")
  const periode = page.getByText(/Période de paie/)
  const avant = await periode.innerText()
  await page.getByRole("combobox").filter({ hasText: "Novembre" }).click()
  await page.getByRole("option", { name: "Octobre" }).click()
  await expect(periode).not.toHaveText(avant)
})

test("thème : le choix « Sombre » pose la classe dark et survit au rechargement", async ({ page }) => {
  await page.goto("/settings")
  await page.getByRole("radio", { name: "Sombre" }).click()
  await expect(page.locator("html")).toHaveClass(/dark/)
  await page.reload()
  await expect(page.locator("html")).toHaveClass(/dark/)
  await page.getByRole("radio", { name: "Clair" }).click()
  await expect(page.locator("html")).not.toHaveClass(/dark/)
})

test("mode confidentialité : les montants du tableau de bord sont masqués", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("button", { name: "Masquer" }).click()
  await expect(page.locator(".privacy-masked").first()).toBeVisible()
  await page.getByRole("button", { name: "Afficher" }).click()
  await expect(page.locator("body")).not.toHaveClass(/privacy-enabled/)
})
