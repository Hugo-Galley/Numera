import { test, expect } from "@playwright/test"

test("mode confidentialité : activation, persistance au rechargement, désactivation", async ({ page }) => {
  await page.goto("/")
  const body = page.locator("body")
  await expect(body).not.toHaveClass(/privacy-enabled/)

  await page.getByRole("button", { name: "Masquer" }).click()
  await expect(body).toHaveClass(/privacy-enabled/)

  await page.reload()
  await expect(body).toHaveClass(/privacy-enabled/)

  await page.getByRole("button", { name: "Afficher" }).click()
  await expect(body).not.toHaveClass(/privacy-enabled/)
})
