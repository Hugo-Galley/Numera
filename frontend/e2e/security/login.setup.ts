import { test as setup, expect } from "@playwright/test"

import { CREDENTIALS, SECURITY_STATE } from "./support"

// Connexion faite une fois sur la pile « sécurité » ; les scénarios réutilisent la session.
setup("connexion (profil security)", async ({ page }) => {
  await page.goto("/login")
  await page.getByLabel("Utilisateur").fill(CREDENTIALS.username)
  await page.getByLabel("Mot de passe").fill(CREDENTIALS.password)
  await page.getByRole("button", { name: "Se connecter" }).click()
  await expect(page).not.toHaveURL(/\/login/)
  await page.context().storageState({ path: SECURITY_STATE })
})
