import { test, expect, confirmDialog, unique } from "./fixtures"

test("épargne : bilan financier, flux et historique", async ({ page }) => {
  await page.goto("/savings")
  await expect(page.getByRole("heading", { level: 1, name: "Suivi de l'Épargne" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Bilan Financier" })).toBeVisible()
  await expect(page.getByText("Patrimoine Net Total")).toBeVisible()
  await expect(page.getByRole("heading", { name: "Historique des Flux d'Épargne" })).toBeVisible()
})

test("objectif d'épargne : création, visible avec sa cible, suppression", async ({ page }) => {
  const name = unique("Objectif")
  await page.goto("/savings")
  await page.getByRole("button", { name: "Nouvel Objectif" }).click()
  await page.getByRole("textbox", { name: "Nom de l'objectif" }).fill(name)
  await page.getByRole("spinbutton", { name: "Montant cible (€)" }).fill("5000")
  await page.getByRole("button", { name: "Créer l'objectif" }).click()
  await expect(page.getByRole("heading", { name, level: 3 })).toBeVisible()

  const carte = page.locator("div").filter({ has: page.getByRole("heading", { name, level: 3 }) }).filter({ has: page.getByRole("button", { name: "Supprimer l'objectif" }) }).last()
  await expect(page.getByText(/sur 5.000,00/).first()).toBeVisible()
  await carte.getByRole("button", { name: "Supprimer l'objectif" }).click()
  await confirmDialog(page)
  await expect(page.getByRole("heading", { name, level: 3 })).toHaveCount(0)
})
