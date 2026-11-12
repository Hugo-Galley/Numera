import { test, expect, submitButton } from "./fixtures"

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
  await page.getByRole("button", { name: submitButton }).click()
  await expect(page).toHaveURL(/\/login/)
  await expect(page.getByRole("button", { name: submitButton })).toBeEnabled()
})

test("bons identifiants : on arrive sur le tableau de bord et on revient à la page demandée", async ({ page }) => {
  await page.goto("/accounts")
  await expect(page).toHaveURL(/\/login/)
  await page.getByLabel("Utilisateur").fill("demo")
  await page.getByLabel("Mot de passe").fill("demo")
  await page.getByRole("button", { name: submitButton }).click()
  await expect(page).toHaveURL(/\/accounts$/)
})

test.describe("session expirée", () => {
  // L'application journalise l'échec de chargement avant de renvoyer vers la connexion : attendu ici.
  test.use({ ignoredErrors: [/Session expirée/] })

  test("401 du serveur : retour à la connexion", async ({ page }) => {
    await page.goto("/login")
    await page.getByLabel("Utilisateur").fill("demo")
    await page.getByLabel("Mot de passe").fill("demo")
    await page.getByRole("button", { name: submitButton }).click()
    await expect(page).not.toHaveURL(/\/login/)

    await page.route("http://localhost:8101/accounts", (route) => route.fulfill({ status: 401, json: { detail: "Token expiré" } }))
    await page.goto("/accounts")
    await expect(page).toHaveURL(/\/login/)
  })
})
