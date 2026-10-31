import { test, expect } from "@playwright/test"

// Ces scénarios partent d'un navigateur non connecté.
test.use({ storageState: { cookies: [], origins: [] } })

test("une page protégée renvoie vers la connexion", async ({ page }) => {
  await page.goto("/accounts")
  await expect(page).toHaveURL(/\/login/)
})

test("mauvais mot de passe : erreur, on reste sur la connexion", async ({ page }) => {
  await page.goto("/login")
  await page.getByLabel("Utilisateur").fill("demo")
  await page.getByLabel("Mot de passe").fill("mauvais")
  await page.getByRole("button", { name: /Entrer dans la démo|Se connecter/ }).click()
  await expect(page).toHaveURL(/\/login/)
  await expect(page.getByRole("button", { name: /Entrer dans la démo|Se connecter/ })).toBeEnabled()
})

test("bons identifiants : on arrive sur le tableau de bord et on revient à la page demandée", async ({ page }) => {
  await page.goto("/accounts")
  await expect(page).toHaveURL(/\/login/)
  await page.getByLabel("Utilisateur").fill("demo")
  await page.getByLabel("Mot de passe").fill("demo")
  await page.getByRole("button", { name: /Entrer dans la démo|Se connecter/ }).click()
  await expect(page).toHaveURL(/\/accounts$/)
})
