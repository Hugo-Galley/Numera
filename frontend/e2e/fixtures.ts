import { test as base, expect, type Page } from "@playwright/test"

export { expect }

/**
 * `test` commun à tous les scénarios :
 * - la pop-up « mois à clôturer » du tableau de bord est neutralisée (elle masquerait la page) ;
 * - une garde transversale échoue le scénario sur toute exception JS, erreur console applicative
 *   ou réponse HTTP 5xx, quelle que soit la page visitée. Un scénario qui provoque volontairement
 *   une erreur 4xx n'est pas concerné : seules les 5xx et les exceptions sont fatales.
 */
export const test = base.extend<{ guard: void; ignoredErrors: RegExp[]; expectedServerErrors: RegExp[] }>({
  // Erreurs console attendues par un scénario précis (`test.use({ ignoredErrors: [/motif/] })`), jamais globales.
  ignoredErrors: [[], { option: true }],
  // Réponses 5xx voulues par un scénario (ex. canal de notification injoignable → 502), par motif d'URL.
  expectedServerErrors: [[], { option: true }],
  page: async ({ page }, provide) => {
    await page.addInitScript(() => {
      const get = Storage.prototype.getItem
      Storage.prototype.getItem = function (key: string) {
        return key.startsWith("month-review-skip-") ? "1" : get.call(this, key)
      }
    })
    await provide(page)
  },
  guard: [
    async ({ page, ignoredErrors, expectedServerErrors }, provide) => {
      const problems: string[] = []
      page.on("pageerror", (e) => problems.push(`exception : ${e.message}`))
      page.on("console", (m) => {
        // Les « Failed to load resource » 4xx sont des réponses attendues (mauvais mot de passe…) : la 5xx est captée plus bas.
        const text = m.text()
        if (m.type() === "error" && !text.startsWith("Failed to load resource") && !ignoredErrors.some((re) => re.test(text))) {
          problems.push(`console : ${text}`)
        }
      })
      page.on("response", (r) => r.status() >= 500 && !expectedServerErrors.some((re) => re.test(r.url())) && problems.push(`HTTP ${r.status()} : ${r.url()}`))
      await provide()
      expect(problems, "erreurs applicatives pendant le scénario").toEqual([])
    },
    { auto: true },
  ],
})

/** Le suffixe rend les données créées uniques : un scénario peut être relancé sur la même base. */
export const unique = (label: string) => `E2E ${label} ${Date.now().toString(36)}`

/** Les listes existent en deux mises en page (mobile / bureau) : on ne retient que celle qui est visible. */
export const visible = (page: Page, text: string) => page.getByText(text, { exact: true }).locator("visible=true")

/** Ouvre la fiche d'un compte de la démo depuis la liste (Compte courant, Livret A, PEA, Assurance-vie). */
export async function openAccount(page: Page, name: string) {
  await page.goto("/accounts")
  await page.getByRole("row", { name: new RegExp(`^Favori ${name}`) }).getByRole("link", { name: "Voir détails" }).click()
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible()
}

/** Ouvre le menu « Actions » de la ligne de transaction contenant `merchant`. */
export async function openTransactionMenu(page: Page, merchant: string) {
  await page.getByRole("row", { name: new RegExp(merchant) }).first().getByRole("button", { name: "Actions" }).click()
}

export const submitButton = /Entrer dans la démo|Se connecter/

/** Valide la boîte de confirmation de l'application (`useConfirm`), ouverte par une action destructive. */
export async function confirmDialog(page: Page) {
  await page.getByRole("dialog").getByRole("button", { name: /^(Supprimer|Confirmer|Archiver|Désarchiver|Clôturer)$/ }).click()
}
