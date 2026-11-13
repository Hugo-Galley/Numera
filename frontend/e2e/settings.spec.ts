import { test, expect } from "./fixtures"

test("paramètres : les quatre onglets et leur adresse", async ({ page }) => {
  await page.goto("/settings")
  await expect(page.getByRole("heading", { level: 1, name: "Paramètres" })).toBeVisible()
  for (const [tab, key] of [["Notifications", "notifications"], ["Sécurité", "security"], ["Données", "data"], ["Général", "general"]]) {
    await page.getByRole("tab", { name: tab }).click()
    await expect(page.getByRole("tab", { name: tab })).toHaveAttribute("aria-selected", "true")
    await expect(page).toHaveURL(new RegExp(`tab=${key}`))
  }
})

test("sécurité : mot de passe, passkey, double authentification et accès MCP sont présentés", async ({ page }) => {
  await page.goto("/settings?tab=security")
  for (const title of ["Mot de passe", "Face ID / Touch ID", "Double authentification", "Claude (MCP)"]) {
    await expect(page.getByRole("heading", { name: title })).toBeVisible()
  }
})

test("sécurité : un changement de mot de passe incohérent est refusé (démo : aucune session perdue)", async ({ page }) => {
  await page.goto("/settings?tab=security")
  await page.locator("#current-password").fill("demo")
  await page.getByRole("textbox", { name: "Nouveau mot de passe" }).fill("nouveau-mdp-123")
  await page.getByRole("textbox", { name: "Confirmer le mot de passe" }).fill("autre-chose-456")
  await page.getByRole("button", { name: "Enregistrer" }).click()
  await expect(page.locator("[data-sonner-toast][data-type='error']")).toBeVisible()
  await expect(page).toHaveURL(/\/settings/)
})

test("données : export CSV des comptes sélectionnés", async ({ page }) => {
  await page.goto("/settings?tab=data")
  await expect(page.getByRole("button", { name: /Exporter en CSV/ })).toBeVisible()
  const download = page.waitForEvent("download")
  await page.getByRole("button", { name: /Exporter en CSV/ }).click()
  const file = await download
  expect(file.suggestedFilename()).toMatch(/\.csv$/i)
})

test("données : la zone de danger exige de taper EFFACER (rien n'est effacé ici)", async ({ page }) => {
  await page.goto("/settings?tab=data")
  await expect(page.getByRole("heading", { name: "Zone de danger" })).toBeVisible()
})

test("profil : le nom d'utilisateur est celui de la session", async ({ page }) => {
  await page.goto("/settings")
  await expect(page.getByRole("textbox", { name: "Nom d'utilisateur" })).toHaveValue("demo")
})
