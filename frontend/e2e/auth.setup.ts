import { test as setup, expect } from "@playwright/test"

export const STORAGE_STATE = "e2e/.auth/state.json"

// Connexion faite une fois ; les autres scénarios réutilisent la session.
setup("connexion", async ({ page }) => {
  await page.goto("/login")
  await page.getByLabel("Utilisateur").fill("demo")
  await page.getByLabel("Mot de passe").fill("demo")
  await page.getByRole("button", { name: /Entrer dans la démo|Se connecter/ }).click()
  await expect(page).not.toHaveURL(/\/login/)
  await page.context().storageState({ path: STORAGE_STATE })
})
