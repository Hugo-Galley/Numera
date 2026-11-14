import { test, expect } from "./fixtures"

test("simulateur : épargner davantage change la projection à 10 ans", async ({ page }) => {
  await page.goto("/tools")
  const projection = page.getByRole("heading", { level: 3 }).filter({ hasText: /€/ }).first()
  const avant = await projection.innerText()
  await page.getByRole("button", { name: "+200 €" }).click()
  await expect(projection).not.toHaveText(avant)
  await page.getByRole("button", { name: "20 ans" }).click()
  await expect(page.getByText(/Dans 20 ans/)).toBeVisible()
})

test("simulateur : la section indépendance financière donne un objectif chiffré", async ({ page }) => {
  await page.goto("/tools")
  await expect(page.getByRole("heading", { name: "Indépendance financière" })).toBeVisible()
  await expect(page.getByText("Objectif", { exact: true }).first()).toBeVisible()
})

test("fiscalité : plafonds des enveloppes et ordre de remplissage", async ({ page }) => {
  await page.goto("/tax")
  await expect(page.getByRole("heading", { level: 1, name: "Fiscalité" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Où placer ton prochain euro" })).toBeVisible()
  await expect(page.getByRole("link", { name: "Livret A" }).first()).toBeVisible()
})

test("bilan annuel : récapitulatif et story plein écran", async ({ page }) => {
  await page.goto("/wrapped")
  await expect(page.getByRole("heading", { level: 1, name: "Bilan annuel" })).toBeVisible()
  await page.getByRole("button", { name: "Revivre mon année" }).click()
  await expect(page.getByRole("dialog").or(page.locator(".theme-island").first())).toBeVisible()
  await page.keyboard.press("Escape")
})
