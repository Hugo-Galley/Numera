import { test, expect, openAccount, openTransactionMenu, unique, visible } from "./fixtures"

test("crédit : création depuis la liste des comptes", async ({ page }) => {
  const name = unique("Prêt")
  await page.goto("/accounts")
  await page.getByRole("button", { name: "Ajouter un crédit" }).click()
  await page.getByRole("textbox", { name: "Nom", exact: true }).fill(name)
  await page.getByRole("textbox", { name: "Banque", exact: true }).fill("Banque E2E")
  await page.getByRole("textbox", { name: "Montant emprunté (€)" }).fill("10000")
  await page.getByRole("textbox", { name: "Taux nominal annuel (%)" }).fill("3")
  await page.getByRole("textbox", { name: "Durée (années)" }).fill("5")
  await page.getByRole("dialog").getByRole("button", { name: "Enregistrer" }).click()
  await expect(visible(page, name)).toBeVisible()
})

test("remboursements : déclarer une créance depuis une dépense", async ({ page }) => {
  const label = unique("Avance")
  const debtor = unique("Ami")
  await openAccount(page, "Compte courant")
  await page.getByRole("button", { name: "Nouvelle opération" }).click()
  await page.getByRole("combobox", { name: "Commerçant / Libellé" }).fill(label)
  await page.getByRole("spinbutton", { name: "Montant" }).fill("40")
  await page.getByRole("button", { name: "Enregistrer" }).click()

  await openTransactionMenu(page, label)
  await page.getByRole("menuitem", { name: "On me doit…" }).click()
  const dialog = page.getByRole("dialog")
  await expect(dialog).toBeVisible()
  await dialog.getByRole("textbox", { name: "Qui me doit" }).fill(debtor)
  await dialog.getByRole("textbox", { name: "Montant", exact: true }).fill("40")
  await dialog.getByRole("button", { name: "Ajouter" }).click()
  await expect(dialog.getByText(/Déclaré : 40,00/)).toBeVisible()
  await page.keyboard.press("Escape")

  await page.goto("/reimbursements")
  await expect(visible(page, debtor).first()).toBeVisible()
})
