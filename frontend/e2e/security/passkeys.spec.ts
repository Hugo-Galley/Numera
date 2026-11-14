import { test, expect } from "../fixtures"
import { CREDENTIALS, openSecurity } from "./support"

// Authentificateur WebAuthn virtuel de Chromium (CDP) : ni Touch ID ni clé physique. localhost est un contexte sûr.
test("passkey : enregistrement, connexion sans mot de passe, suppression", async ({ page, context }) => {
  const cdp = await context.newCDPSession(page)
  await cdp.send("WebAuthn.enable")
  await cdp.send("WebAuthn.addVirtualAuthenticator", {
    options: {
      protocol: "ctap2",
      transport: "internal",
      hasResidentKey: true,
      hasUserVerification: true,
      isUserVerified: true,
      automaticPresenceSimulation: true,
    },
  })

  await openSecurity(page)
  await page.getByRole("button", { name: "Ajouter une passkey" }).click()
  await page.getByRole("dialog").getByLabel("Mot de passe actuel").fill(CREDENTIALS.password)
  await page.getByRole("dialog").getByRole("button", { name: "Confirmer" }).click()
  await expect(page.locator("[data-sonner-toast][data-type='success']").first()).toBeVisible()
  const remove = page.getByRole("button", { name: /^Supprimer (Mac|Appareil|iPhone)/ })
  await expect(remove).toHaveCount(1)

  // Nouvelle session sans mot de passe : la page de connexion propose la passkey dès l'ouverture
  await page.evaluate(() => localStorage.clear())
  await page.goto("/login")
  await expect(page).not.toHaveURL(/\/login/)
  await page.goto("/settings?tab=security")
  await expect(page.getByText(/utilisée le/)).toBeVisible()

  await remove.click()
  await page.getByRole("dialog").getByRole("button", { name: "Supprimer" }).click()
  await page.getByRole("dialog").getByLabel("Mot de passe actuel").fill(CREDENTIALS.password)
  await page.getByRole("dialog").getByRole("button", { name: "Confirmer" }).click()
  await expect(remove).toHaveCount(0)
})
