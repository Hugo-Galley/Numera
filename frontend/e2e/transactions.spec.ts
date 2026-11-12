import { test, expect, confirmDialog, openAccount, openTransactionMenu, unique, visible } from "./fixtures"

test("saisie d'une dépense : visible dans l'historique, puis modifiée", async ({ page }) => {
  const label = unique("Dépense")
  await openAccount(page, "Compte courant")

  await page.getByRole("button", { name: "Nouvelle opération" }).click()
  await page.getByRole("combobox", { name: "Commerçant / Libellé" }).fill(label)
  await page.getByRole("spinbutton", { name: "Montant" }).fill("23.5")
  await page.getByRole("button", { name: "Enregistrer" }).click()
  await expect(visible(page, label)).toBeVisible()

  await openTransactionMenu(page, label)
  await page.getByRole("menuitem", { name: "Modifier" }).click()
  await page.getByRole("spinbutton", { name: "Montant" }).fill("31")
  await page.getByRole("button", { name: "Enregistrer" }).click()
  await expect(page.getByRole("row", { name: new RegExp(label) }).first()).toContainText("31,00")
})

test("suppression d'une opération avec confirmation", async ({ page }) => {
  const label = unique("À supprimer")
  await openAccount(page, "Compte courant")
  await page.getByRole("button", { name: "Nouvelle opération" }).click()
  await page.getByRole("combobox", { name: "Commerçant / Libellé" }).fill(label)
  await page.getByRole("spinbutton", { name: "Montant" }).fill("5")
  await page.getByRole("button", { name: "Enregistrer" }).click()
  await expect(visible(page, label)).toBeVisible()

  await openTransactionMenu(page, label)
  await page.getByRole("menuitem", { name: "Supprimer" }).click()
  await confirmDialog(page)
  await expect(visible(page, label)).toHaveCount(0)
})

test("recherche et filtres de l'historique", async ({ page }) => {
  await openAccount(page, "Compte courant")
  const rows = page.getByRole("row", { name: /Netflix/ })
  await page.getByRole("textbox", { name: "Rechercher..." }).fill("Netflix")
  await expect(rows.first()).toBeVisible()
  await expect(page.getByRole("row", { name: /Lidl/ })).toHaveCount(0)

  await page.getByRole("textbox", { name: "Rechercher..." }).fill("")
  await page.getByRole("combobox").filter({ hasText: "Tous types" }).click()
  await page.getByRole("option", { name: /Entrée/ }).click()
  await expect(page.getByRole("row", { name: /Netflix/ })).toHaveCount(0)
})

test("virement interne : le panneau propose de créer la contrepartie", async ({ page }) => {
  await openAccount(page, "Compte courant")
  await openTransactionMenu(page, "Spotify")
  await page.getByRole("menuitem", { name: /Virement interne/ }).click()
  const dialog = page.getByRole("dialog", { name: "Virement interne" })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole("button", { name: "Créer et lier" })).toBeDisabled()
  await dialog.getByRole("button", { name: "Close" }).click()
  await expect(dialog).toBeHidden()
})
