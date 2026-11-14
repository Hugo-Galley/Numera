import { test, expect, confirmDialog, unique, visible } from "./fixtures"

test("échéances : analyse des abonnements, bascule en liste et calendrier", async ({ page }) => {
  await page.goto("/recurring")
  await expect(page.getByRole("heading", { level: 1, name: "Échéances" })).toBeVisible()
  await expect(page.getByText("Coût Mensuel Total")).toBeVisible()
  await expect(page.getByRole("heading", { name: "Abonnements confirmés" })).toBeVisible()

  await page.getByRole("button", { name: "Liste" }).click()
  await expect(visible(page, "Netflix")).toBeVisible()

  await page.getByRole("tab", { name: "Calendrier" }).click()
  await expect(page).toHaveURL(/tab=calendar/)
  await page.getByRole("button", { name: "Mois suivant" }).click()
  await expect(page.getByRole("button", { name: "Mois précédent" })).toBeVisible()
})

test("récurrence : création puis suppression", async ({ page }) => {
  const name = unique("Rec")
  await page.goto("/recurring")
  await page.getByRole("button", { name: "Liste" }).click()
  await page.getByRole("button", { name: "Nouvelle récurrence" }).click()
  await page.getByRole("textbox", { name: "Nom / Marchand" }).fill(name)
  await page.getByRole("spinbutton", { name: "Montant" }).fill("9.99")
  await page.getByRole("dialog").getByRole("button", { name: /^(Créer|Enregistrer)/ }).click()
  await expect(visible(page, name)).toBeVisible()

  const carte = page.getByRole("row").filter({ hasText: name })
  await carte.getByRole("button", { name: "Supprimer" }).click()
  await confirmDialog(page)
  await expect(page.getByText(name, { exact: true })).toHaveCount(0)
})

test("salaire et aides : la configuration du salaire est lisible", async ({ page }) => {
  await page.goto("/recurring?tab=salary")
  await expect(page.getByRole("heading", { name: "Configuration Salaire & Avantages" })).toBeVisible()
  await expect(page.getByRole("spinbutton").first()).toHaveValue("2000")
  await page.getByRole("button", { name: "Aides" }).click()
  await expect(page).toHaveURL(/vue=aides/)
})
