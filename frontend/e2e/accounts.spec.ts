import { test, expect, openAccount, confirmDialog, unique } from "./fixtures"

test("liste des comptes : les quatre comptes de la démo avec leur solde", async ({ page }) => {
  await page.goto("/accounts")
  await expect(page.getByRole("heading", { level: 1, name: "Comptes" })).toBeVisible()
  for (const name of ["Compte courant", "Livret A", "PEA", "Assurance-vie"]) {
    await expect(page.getByRole("row", { name: new RegExp(`^Favori ${name}`) })).toContainText("€")
  }
})

test("détail d'un compte : KPI, graphique, historique des transactions", async ({ page }) => {
  await openAccount(page, "Compte courant")
  await expect(page.getByText("Solde Actuel")).toBeVisible()
  await expect(page.getByRole("heading", { name: "Évolution du solde" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Historique", level: 2 })).toBeVisible()
  expect(await page.getByRole("row").count()).toBeGreaterThan(5)
})

test("création, modification puis archivage d'un compte", async ({ page }) => {
  const name = unique("Compte")
  const renamed = `${name} bis`
  await page.goto("/accounts")

  await page.getByRole("button", { name: "Ajouter un compte" }).click()
  await page.getByRole("textbox", { name: "Nom du compte" }).fill(name)
  await page.getByRole("combobox", { name: "Établissement / Banque" }).fill("Banque E2E")
  await page.getByRole("button", { name: "Créer" }).click()
  await expect(page.getByText("Compte créé")).toBeVisible()
  const row = (n: string) => page.getByRole("row", { name: new RegExp(`^Favori ${n}`) })
  await expect(row(name)).toBeVisible()

  await row(name).getByRole("button", { name: "Modifier" }).click()
  await page.getByRole("textbox", { name: "Nom du compte" }).fill(renamed)
  await page.getByRole("button", { name: "Enregistrer" }).click()
  await expect(row(renamed)).toBeVisible()

  await row(renamed).getByRole("button", { name: "Archiver" }).click()
  await confirmDialog(page)
  await expect(row(renamed)).toHaveCount(0)
})

test("rapprochement avec la banque : un solde identique marque le compte vérifié", async ({ page }) => {
  await openAccount(page, "Livret A")
  const solde = (await page.getByText("Solde Actuel").locator("xpath=following::h3[1]").innerText()).replace(/[^\d,-]/g, "")
  await page.getByRole("button", { name: "Rapprocher" }).click()
  await page.getByRole("textbox", { name: /Solde banque/ }).fill(solde)
  await page.getByRole("button", { name: "Vérifier" }).click()
  await expect(page.getByText(/Solde vérifié le/)).toBeVisible()
})
