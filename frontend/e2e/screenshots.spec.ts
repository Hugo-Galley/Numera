import { test } from "@playwright/test"

// Captures du README (docs/screenshots/), prises sur la base de démo jetable en haute définition.
// Ignoré par défaut : `npm run screenshots` (SCREENSHOTS=1).
test.skip(!process.env.SCREENSHOTS, "captures du README : lancer `npm run screenshots`")

test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })

const PAGES: [string, string][] = [
  ["dashboard", "/"],
  ["bilan-mois", "/month/bilan"],
  ["centre-actions", "/audit"],
  ["echeances", "/recurring"],
  ["epargne", "/savings"],
  ["investissements", "/investments"],
]

for (const [name, route] of PAGES) {
  test(`capture ${name}`, async ({ page }) => {
    await page.goto(route)
    await page.waitForLoadState("networkidle")
    // Rappel de clôture du mois : une popin masquerait la page
    const dialog = page.getByRole("dialog")
    if (await dialog.isVisible({ timeout: 1500 }).catch(() => false)) {
      await page.keyboard.press("Escape")
      await dialog.waitFor({ state: "hidden" })
    }
    await page.addStyleTag({ content: "*, *::before, *::after { caret-color: transparent !important }" })
    await page.waitForTimeout(2000) // fin des animations des graphiques
    await page.screenshot({ path: `../docs/screenshots/${name}.png` })
  })
}
