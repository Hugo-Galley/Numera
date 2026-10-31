import { test, expect } from "@playwright/test"

test("règle de catégorisation : création puis suppression", async ({ page }) => {
  await page.goto("/classement?tab=rules")

  await page.getByRole("button", { name: "Nouvelle règle" }).first().click()
  await page.getByPlaceholder("Ex: Uber, Netflix, Carrefour...").fill("E2E-REGLE")
  await page.getByRole("button", { name: "Créer la règle" }).click()
  await expect(page.getByText("Règle créée avec succès")).toBeVisible()
  await expect(page.getByText("E2E-REGLE").first()).toBeVisible()

  await page.getByText("E2E-REGLE").first().locator("xpath=ancestor::div[contains(@class,'justify-between')][1]").getByRole("button", { name: "Supprimer" }).click()
  const confirm = page.getByRole("button", { name: /Supprimer|Confirmer/ }).last()
  if (await confirm.isVisible()) await confirm.click()
  await expect(page.getByText("E2E-REGLE")).toHaveCount(0)
})
