import { test, expect } from "../fixtures"
import { CREDENTIALS, MOCK, mockLog, openSecurity } from "./support"

// Aucun vrai réseau : ntfy pointe sur le faux serveur local, Telegram (adresse figée dans le backend) passe par un
// proxy qui refuse tout CONNECT (cf. backend-security.sh) et le journalise.
// L'essai Telegram échoue volontairement : le backend répond 502 (canal injoignable), pas une régression
test.use({ expectedServerErrors: [/\/notifications\/test$/] })

async function save(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: "Enregistrer", exact: true }).click()
  // Changer une destination d'envoi exige le mot de passe
  await page.getByRole("dialog").getByLabel("Mot de passe actuel").fill(CREDENTIALS.password)
  await page.getByRole("dialog").getByRole("button", { name: "Confirmer" }).click()
  await expect(page.locator("[data-sonner-toast][data-type='success']").first()).toBeVisible()
}

// Valeurs propres à chaque exécution : sur une pile réutilisée en local, « Enregistrer » resterait inactif sinon
const topic = `e2e-${Date.now().toString(36)}`
const chat = String(Date.now())

test("notifications : réglages ntfy enregistrés puis message d'essai reçu par le serveur simulé", async ({ page, request }) => {
  await request.delete(`${MOCK}/__requests`)
  await openSecurity(page, "notifications")
  await page.getByLabel("Serveur").fill(MOCK)
  await page.getByLabel("Sujet").fill(topic)
  await page.getByLabel("Jeton d'accès (facultatif)").fill("tk_e2e_secret")
  await save(page)

  await page.reload()
  await expect(page.getByLabel("Serveur")).toHaveValue(MOCK)
  await expect(page.getByLabel("Sujet")).toHaveValue(topic)
  await expect(page.getByLabel("Jeton d'accès (facultatif)")).toHaveValue("••••cret") // jeton masqué par le backend

  await page.getByRole("button", { name: "Envoyer un test" }).first().click()
  await expect(page.locator("[data-sonner-toast][data-type='success']").first()).toBeVisible()
  const sent = (await mockLog(request)).filter((r) => r.kind === "http")
  expect(sent).toHaveLength(1)
  expect(sent[0]).toMatchObject({ method: "POST", auth: "Bearer tk_e2e_secret", body: { topic } })
})

test("notifications : réglages Telegram enregistrés, jeton masqué, essai refusé sans sortir du poste", async ({ page, request }) => {
  await request.delete(`${MOCK}/__requests`)
  await openSecurity(page, "notifications")
  await page.getByLabel("Jeton du bot").fill("123456:E2E-fake-bot-token")
  await page.getByLabel("Chat ID").fill(chat)
  await save(page)

  await page.reload()
  await expect(page.getByLabel("Jeton du bot")).toHaveValue("••••oken")
  await expect(page.getByLabel("Chat ID")).toHaveValue(chat)

  await page.getByRole("button", { name: "Envoyer un test" }).last().click()
  await expect(page.locator("[data-sonner-toast][data-type='error']").first()).toBeVisible()
  const log = await mockLog(request)
  expect(log).toContainEqual({ kind: "connect", target: "api.telegram.org:443" })
})
