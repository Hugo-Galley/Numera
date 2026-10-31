import fs from "node:fs"
import { test, expect, type Page } from "@playwright/test"

// Dates du mois courant : les lignes restent dans la période affichée par défaut sur le compte.
function releve(path: string) {
  const now = new Date()
  const day = (d: number) => `${String(d).padStart(2, "0")}/${String(now.getMonth() + 1).padStart(2, "0")}/${now.getFullYear()}`
  fs.writeFileSync(
    path,
    [
      "Date;Type;Commercant;Categorie;Montant",
      `${day(1)};Sortie;E2E Boulangerie;Alimentation;12,50`,
      `${day(1)};Sortie;E2E Librairie;Loisirs;30,00`,
      `${day(1)};Entree;E2E Remboursement;Autres;45,00`,
    ].join("\n"),
  )
}

// La liste des transactions existe en deux mises en page (mobile / bureau) : on ne compte que la visible.
const visible = (page: Page, text: string) => page.getByText(text, { exact: true }).locator("visible=true")

test("import CSV : aperçu, import, lignes visibles sur le compte, ré-import sans doublon", async ({ page }, testInfo) => {
  const csv = testInfo.outputPath("releve.csv")
  releve(csv)

  await page.goto("/accounts")
  await page.getByRole("link", { name: "Voir détails" }).first().click()
  await expect(page).toHaveURL(/\/accounts\/\d+/)

  await page.getByRole("button", { name: "Importer" }).click()
  await page.locator('input[type="file"]').setInputFiles(csv)
  await expect(page.getByText("Aperçu des données")).toBeVisible()
  await expect(page.getByRole("cell", { name: "E2E Boulangerie" })).toBeVisible()

  await page.getByRole("button", { name: "Lancer l'importation" }).click()
  await expect(page.getByText("Importation réussie")).toBeVisible()
  await page.keyboard.press("Escape")

  await expect(visible(page, "E2E Boulangerie")).toBeVisible()
  await expect(visible(page, "E2E Librairie")).toBeVisible()

  // Idempotence : le même fichier ne crée aucun doublon
  await page.getByRole("button", { name: "Importer" }).click()
  await page.locator('input[type="file"]').setInputFiles(csv)
  await page.getByRole("button", { name: "Lancer l'importation" }).click()
  await expect(page.getByText("Importation réussie")).toBeVisible()
  await page.keyboard.press("Escape")
  await expect(visible(page, "E2E Boulangerie")).toHaveCount(1)
})
