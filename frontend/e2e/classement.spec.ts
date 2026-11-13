import { test, expect, confirmDialog, unique } from "./fixtures"

test("classement : les quatre onglets s'ouvrent et portent l'adresse ?tab=", async ({ page }) => {
  await page.goto("/classement")
  for (const [tab, key] of [["Tags", "tags"], ["Marchands", "merchants"], ["Règles", "rules"], ["Catégories", "categories"]]) {
    await page.getByRole("tab", { name: tab }).click()
    await expect(page.getByRole("tab", { name: tab })).toHaveAttribute("aria-selected", "true")
    await expect(page).toHaveURL(new RegExp(`tab=${key}`))
  }
})

test("catégories : création puis suppression", async ({ page }) => {
  const name = unique("Cat")
  await page.goto("/classement?tab=categories")
  await page.getByRole("button", { name: "Nouvelle catégorie" }).click()
  await page.getByRole("textbox", { name: "Nom", exact: true }).fill(name)
  await page.getByRole("button", { name: /^(Créer|Enregistrer)/ }).click()
  const entry = page.locator("div").filter({ has: page.getByText(name, { exact: true }) }).filter({ has: page.getByRole("button", { name: "Supprimer" }) }).last()
  await expect(page.getByText(name, { exact: true })).toBeVisible()

  await entry.getByRole("button", { name: "Supprimer" }).click()
  await confirmDialog(page)
  await expect(page.getByText(name, { exact: true })).toHaveCount(0)
})

test("tags : création puis suppression", async ({ page }) => {
  const name = unique("Tag")
  await page.goto("/classement?tab=tags")
  await page.getByRole("button", { name: "Nouveau tag" }).click()
  await page.getByRole("textbox").first().fill(name)
  await page.getByRole("button", { name: /^(Créer|Enregistrer|Ajouter)/ }).click()
  await expect(page.getByText(name, { exact: true })).toBeVisible()

  const entry = page.locator("div").filter({ has: page.getByText(name, { exact: true }) }).filter({ has: page.getByRole("button", { name: "Supprimer" }) }).last()
  await entry.getByRole("button", { name: "Supprimer" }).click()
  await confirmDialog(page)
  await expect(page.getByText(name, { exact: true })).toHaveCount(0)
})

test("marchands : suggestions de libellés fréquents et recherche", async ({ page }) => {
  await page.goto("/classement?tab=merchants")
  await expect(page.getByRole("heading", { name: "Suggestions" })).toBeVisible()
  await expect(page.getByRole("button", { name: "Créer un marchand à partir de ce libellé" }).first()).toBeVisible()
  await page.getByRole("searchbox", { name: /Rechercher un marchand/ }).fill("zzz-introuvable")
  await expect(page.getByText("Aucun marchand trouvé.")).toBeVisible()
})
