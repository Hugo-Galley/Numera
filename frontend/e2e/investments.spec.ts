import { test, expect, openAccount } from "./fixtures"

test("vue globale : valeur, performance, répartition par compte et analyses", async ({ page }) => {
  await page.goto("/investments")
  await expect(page.getByRole("heading", { level: 1, name: "Investissements" })).toBeVisible()
  for (const kpi of ["Valeur Totale", "Performance Globale", "Score de Diversité"]) {
    await expect(page.getByRole("heading", { name: kpi })).toBeVisible()
  }
  await expect(page.getByRole("heading", { name: "Répartition par compte" })).toBeVisible()
  await expect(page.getByText("PEA", { exact: true }).first()).toBeVisible()
  await expect(page.getByText("Assurance-vie", { exact: true }).first()).toBeVisible()
  await expect(page.getByRole("heading", { name: "Analyses avancées" })).toBeVisible()
})

test("compte titres (PEA) : positions valorisées, filtre par type et recherche", async ({ page }) => {
  await openAccount(page, "PEA")
  await expect(page.getByRole("heading", { name: "Positions Actuelles (Actions & ETFs)" })).toBeVisible()
  const ligne = (nom: string) => page.getByRole("row", { name: new RegExp(`^${nom} ${nom}`) })
  await expect(ligne("Amundi MSCI World")).toBeVisible()
  await expect(ligne("TotalEnergies")).toBeVisible()

  await page.getByRole("textbox", { name: "Nom, ticker, ISIN…" }).fill("TTE.PA")
  await expect(ligne("TotalEnergies")).toBeVisible()
  await expect(ligne("Amundi MSCI World")).toHaveCount(0)
})

test("Point Zéro : le panneau liste les positions déclarées et se ferme sans rien modifier", async ({ page }) => {
  await openAccount(page, "PEA")
  await page.getByRole("button", { name: "Point Zéro / État des Lieux" }).click()
  const dialog = page.getByRole("dialog", { name: /Point Zéro/ })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText(/Valeur totale estimée/)).toBeVisible()
  await expect(dialog.getByRole("spinbutton").first()).toHaveValue("16")
  await dialog.getByRole("button", { name: "Annuler" }).click()
  await expect(dialog).toBeHidden()
})

test("assurance-vie : la fiche du compte se charge avec ses indicateurs", async ({ page }) => {
  await openAccount(page, "Assurance-vie")
  await expect(page.getByText("Solde Actuel")).toBeVisible()
})
