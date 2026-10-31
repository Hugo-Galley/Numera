import { test, expect } from "@playwright/test"

test("déconnexion : retour à la connexion, les pages protégées sont refermées", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("button", { name: /demo/ }).click()
  await page.getByRole("menuitem", { name: "Se déconnecter" }).click()
  await expect(page).toHaveURL(/\/login/)

  await page.goto("/accounts")
  await expect(page).toHaveURL(/\/login/)
})
