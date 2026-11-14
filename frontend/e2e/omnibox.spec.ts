import { test, expect } from "./fixtures"

test("⌘K ouvre la recherche et navigue vers une vue", async ({ page }) => {
  await page.goto("/")
  await page.keyboard.press("ControlOrMeta+k")
  const dialog = page.getByRole("dialog", { name: "Recherche" })
  await expect(dialog).toBeVisible()
  await dialog.getByRole("textbox").fill("épargne")
  await dialog.getByRole("button", { name: "Épargne", exact: true }).click()
  await expect(page).toHaveURL(/\/savings$/)
})

test("la recherche trouve un compte et une transaction", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("button", { name: "Rechercher" }).click()
  const dialog = page.getByRole("dialog", { name: "Recherche" })
  await dialog.getByRole("textbox").fill("Livret")
  await dialog.getByRole("button", { name: /Livret A/ }).first().click()
  await expect(page).toHaveURL(/\/accounts\/\d+/)
  await expect(page.getByRole("heading", { level: 1, name: "Livret A" })).toBeVisible()
})

test("Échap referme la recherche", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("button", { name: "Rechercher" }).click()
  await expect(page.getByRole("dialog", { name: "Recherche" })).toBeVisible()
  await page.keyboard.press("Escape")
  await expect(page.getByRole("dialog", { name: "Recherche" })).toBeHidden()
})
