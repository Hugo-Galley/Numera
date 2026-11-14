import { test, expect } from "../fixtures"
import { CREDENTIALS, API, apiToken, openSecurity } from "./support"

test("jetons MCP : création, affichage unique, lecture seule, révocation", async ({ page, request }) => {
  const name = "E2E MCP lecture seule"
  await openSecurity(page)
  await expect(page.getByText("Aucun token")).toBeVisible()

  await page.getByLabel("Nouveau token").fill(name)
  await page.getByPlaceholder("Mot de passe actuel (requis)").fill(CREDENTIALS.password)
  await page.getByRole("button", { name: "Générer un token" }).click()

  // Le jeton en clair n'est montré qu'une fois, dans l'encadré qui suit la création
  const shown = page.locator("pre").filter({ hasText: /^[A-Za-z0-9_-]{20,}$/ })
  await expect(shown).toBeVisible()
  const token = (await shown.innerText()).trim()
  await expect(page.getByText(`${token.slice(0, 8)}…`)).toBeVisible()
  await page.getByRole("button", { name: "J'ai copié le token" }).click()
  await page.reload()
  await expect(page.getByText(token)).toHaveCount(0)
  await expect(page.getByText(name)).toBeVisible()

  // Lecture seule : GET accepté, toute écriture refusée, même sur une route qu'un token de session pourrait écrire
  const headers = { Authorization: `Bearer ${token}` }
  expect((await request.get(`${API}/accounts`, { headers })).status()).toBe(200)
  const write = await request.post(`${API}/accounts`, { headers, data: { name: "Compte MCP", type: "courant" } })
  expect(write.status()).toBe(403)
  const accounts = await request.get(`${API}/accounts`, { headers: { Authorization: `Bearer ${await apiToken(request)}` } })
  expect(JSON.stringify(await accounts.json())).not.toContain("Compte MCP")
  // /admin est interdit aux jetons MCP : un agent ne peut pas se créer d'autres jetons
  const mint = await request.post(`${API}/admin/mcp-tokens`, { headers, data: { name: "x", current_password: CREDENTIALS.password } })
  expect(mint.status()).toBe(403)

  // Révocation : le jeton cesse de fonctionner
  await page.getByRole("button", { name: `Révoquer ${name}` }).click()
  await page.getByRole("dialog").getByRole("button", { name: "Révoquer" }).click()
  await expect(page.getByText("Aucun token")).toBeVisible()
  expect((await request.get(`${API}/accounts`, { headers })).status()).toBe(401)
})
