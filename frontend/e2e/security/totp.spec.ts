import { type Page } from "@playwright/test"
import { test, expect } from "../fixtures"
import { CREDENTIALS, EMPTY_STATE, enableTwoFactor, openSecurity, resetTwoFactor, totpCode } from "./support"

// Chaque test est indépendant : la 2FA est remise à zéro avant et après (retries et ordre sans effet) et les tests qui
// n'ont pas pour objet l'activation l'activent par l'API.
// Horloge : le code du pas courant sert à l'activation (et devient « déjà utilisé », `activatedAt` fige son instant) ;
// les connexions suivantes utilisent le pas +1 (accepté, fenêtre ±1) ; un pas -5 est hors fenêtre. Aucune attente.
test.beforeEach(resetTwoFactor)
test.afterEach(resetTwoFactor)

async function submitPassword(page: Page) {
  await page.goto("/login")
  await page.getByLabel("Utilisateur").fill(CREDENTIALS.username)
  await page.getByLabel("Mot de passe").fill(CREDENTIALS.password)
  await page.getByRole("button", { name: "Se connecter" }).click()
  await expect(page.getByRole("heading", { name: "Vérification" })).toBeVisible()
}

/** Soumet le code et renvoie le statut HTTP de `/auth/totp/login` (200 accepté, 401 refusé). */
async function submitCode(page: Page, code: string): Promise<number> {
  await page.getByLabel("Code").fill(code)
  const reply = page.waitForResponse((r) => r.url().endsWith("/auth/totp/login"))
  await page.getByRole("button", { name: "Valider" }).click()
  return (await reply).status()
}

async function recoveryCodesShown(page: Page): Promise<string[]> {
  const codes = page.locator("[data-privacy-ignore] .font-mono span")
  await expect(codes).toHaveCount(10)
  return codes.allInnerTexts()
}

test("2FA : activation avec un code, codes de secours affichés", async ({ page }) => {
  await openSecurity(page)
  await page.getByRole("button", { name: "Activer", exact: true }).click()
  await page.locator("#totp-settings-password").fill(CREDENTIALS.password)
  await page.getByRole("button", { name: "Continuer" }).click()
  await expect(page.getByRole("img", { name: "QR code de configuration" })).toBeVisible()
  const secret = (await page.locator("p.font-mono").innerText()).replace(/\s/g, "")
  expect(secret).toMatch(/^[A-Z2-7]{32}$/)

  // Un code faux est refusé, le bon active
  await page.locator("#totp-settings-code").fill(totpCode(secret, -5))
  await page.getByRole("button", { name: "Activer", exact: true }).click()
  await expect(page.locator("[data-sonner-toast][data-type='error']").first()).toBeVisible()
  const activatedAt = Date.now()
  await page.locator("#totp-settings-code").fill(totpCode(secret, 0, activatedAt))
  await page.getByRole("button", { name: "Activer", exact: true }).click()
  await expect(page.getByText("Activée", { exact: true })).toBeVisible()
  const recovery = await recoveryCodesShown(page)
  expect(new Set(recovery).size).toBe(10)
})

test.describe("connexion avec second facteur", () => {
  test.use({ storageState: EMPTY_STATE })

  test("code faux, code déjà utilisé et code hors fenêtre refusés ; code valide accepté", async ({ page, request }) => {
    const { secret, activatedAt } = await enableTwoFactor(request)
    await submitPassword(page)
    for (const bad of [totpCode(secret, -5), totpCode(secret, 0, activatedAt)]) { // hors fenêtre ; pas de l'activation, déjà consommé (rejeu)
      expect(await submitCode(page, bad)).toBe(401)
      await expect(page.getByRole("heading", { name: "Vérification" })).toBeVisible()
    }
    expect(await submitCode(page, totpCode(secret, 1))).toBe(200)
    await expect(page).not.toHaveURL(/\/login/)
  })

  test("un code de secours ouvre la session, puis se régénère (les anciens sont invalidés)", async ({ page, request }) => {
    const { recovery } = await enableTwoFactor(request)
    await submitPassword(page)
    expect(await submitCode(page, recovery[0])).toBe(200)
    await expect(page).not.toHaveURL(/\/login/)

    await openSecurity(page)
    await expect(page.getByText("9 codes de secours restants.")).toBeVisible()
    await page.getByRole("button", { name: "Nouveaux codes de secours" }).click()
    await page.locator("#totp-settings-code").fill(recovery[1])
    await page.getByRole("button", { name: "Générer", exact: true }).click()
    const fresh = await recoveryCodesShown(page)
    expect(fresh.filter((c) => recovery.includes(c))).toEqual([])
  })

  test("un code de secours est à usage unique", async ({ page, request }) => {
    const { recovery } = await enableTwoFactor(request)
    await submitPassword(page)
    expect(await submitCode(page, recovery[0])).toBe(200)
    await expect(page).not.toHaveURL(/\/login/)
    await page.context().clearCookies()
    await page.evaluate(() => localStorage.clear())
    await submitPassword(page)
    expect(await submitCode(page, recovery[0])).toBe(401)
  })

  test("désactivation : mot de passe et code exigés, connexion ensuite sans second facteur", async ({ page, request }) => {
    const { recovery } = await enableTwoFactor(request)
    await submitPassword(page)
    expect(await submitCode(page, recovery[0])).toBe(200)
    await expect(page).not.toHaveURL(/\/login/)

    await openSecurity(page)
    await page.getByRole("button", { name: "Désactiver" }).click()
    await page.locator("#totp-settings-password").fill(CREDENTIALS.password)
    await page.locator("#totp-settings-code").fill(recovery[1])
    await page.getByRole("button", { name: "Désactiver" }).last().click()
    await expect(page.getByText("Activée", { exact: true })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Activer", exact: true })).toBeVisible()

    await page.evaluate(() => localStorage.clear())
    await page.goto("/login")
    await page.getByLabel("Utilisateur").fill(CREDENTIALS.username)
    await page.getByLabel("Mot de passe").fill(CREDENTIALS.password)
    await page.getByRole("button", { name: "Se connecter" }).click()
    await expect(page).not.toHaveURL(/\/login/)
  })
})
