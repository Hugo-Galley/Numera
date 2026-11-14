import { test, expect } from "./fixtures"

test("Centre d'actions : compteurs par priorité et action à traiter", async ({ page }) => {
  await page.goto("/audit")
  await expect(page.getByRole("heading", { level: 1, name: "Centre d'actions" })).toBeVisible()
  for (const label of ["Priorité haute", "Priorité moyenne", "Suggestions"]) {
    await expect(page.getByText(label, { exact: true }).first()).toBeVisible()
  }
  await expect(page.getByText(/Dernière analyse/)).toBeVisible()
})

test("Centre d'actions : l'actualisation relance l'analyse sans erreur", async ({ page }) => {
  await page.goto("/audit")
  const analyse = page.waitForResponse((r) => r.url().includes("/analytics/actions") && r.ok())
  await page.getByRole("button", { name: "Actualiser" }).click()
  await analyse
  await expect(page.getByText(/Dernière analyse/)).toBeVisible()
})

test("virements internes : la revue des candidats s'ouvre", async ({ page }) => {
  await page.goto("/audit")
  await page.getByRole("button", { name: "Virements internes" }).click()
  await expect(page.getByRole("dialog").or(page.getByRole("heading", { name: /Virements internes/ })).first()).toBeVisible()
})
