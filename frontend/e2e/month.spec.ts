import { test, expect, confirmDialog } from "./fixtures"

test("bilan du mois : sections et navigation vers le mois précédent", async ({ page }) => {
  await page.goto("/month/bilan")
  await expect(page.getByRole("heading", { level: 1, name: "Bilan du mois" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Où est passé l'argent ?" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Budget tenu ?" })).toBeVisible()
  await expect(page.getByRole("button", { name: "Mois suivant" })).toBeDisabled()

  await page.getByRole("button", { name: "Mois précédent" }).click()
  await expect(page.getByRole("button", { name: "Mois suivant" })).toBeEnabled()
  await expect(page.getByRole("heading", { name: "Principales catégories" })).toBeVisible()
})

test("comparaison de deux mois : écarts et détail par catégorie", async ({ page }) => {
  await page.goto("/month/comparaison")
  await expect(page.getByText("Écart Revenus")).toBeVisible()
  await expect(page.getByText("Écart Dépenses")).toBeVisible()
  await expect(page.getByRole("heading", { name: "Détail par catégorie" })).toBeVisible()
  await expect(page.getByRole("row").nth(2)).toBeVisible()
})

test("revue de fin de mois : parcours des étapes puis clôture (marquer, pas verrouiller)", async ({ page }) => {
  await page.goto("/month/revue")
  for (const step of ["1. Catégoriser", "2. Soldes", "3. Budget", "4. Fait marquant", "5. Clôturer"]) {
    await page.getByRole("button", { name: step }).click()
  }
  await expect(page.getByText("Dépenses sans catégorie")).toBeVisible()
  await page.getByRole("button", { name: "Clôturer le mois" }).click()
  // La clôture peut demander confirmation selon les points restants
  const dialog = page.getByRole("dialog")
  if (await dialog.isVisible()) await confirmDialog(page)
  await expect(page.getByText(/^Clôturé le/)).toBeVisible()

  // Clôturer marque le mois, ne le verrouille pas : il se rouvre et la clôture survit au rechargement
  await page.reload()
  await page.getByRole("button", { name: "5. Clôturer" }).click()
  await expect(page.getByText(/^Clôturé le/)).toBeVisible()
  await page.getByRole("button", { name: "Rouvrir le mois" }).click()
  await expect(page.getByRole("button", { name: "Clôturer le mois" })).toBeVisible()
})
