import { test, expect, type Page } from "@playwright/test"

const visible = (page: Page, text: string) => page.getByText(text, { exact: true }).locator("visible=true")

test("ajout d'une opération à la main : visible dans le compte", async ({ page }) => {
  await page.goto("/accounts")
  await page.getByRole("link", { name: "Voir détails" }).first().click()
  await expect(page).toHaveURL(/\/accounts\/\d+/)

  await page.getByRole("button", { name: "Nouvelle opération" }).click()
  await page.getByLabel("Commerçant / Libellé").fill("E2E Saisie manuelle")
  await page.locator("#amount").fill("17.40")
  await page.getByRole("button", { name: "Enregistrer" }).click()

  await expect(visible(page, "E2E Saisie manuelle")).toBeVisible()
})
