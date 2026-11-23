/** Formulaire « Nouvelle opération » : champs utiles seulement, montant à la française, focus adapté au mobile (audit visuel). */
import { screen, within } from "@testing-library/react"
import { makeTransaction } from "@/test/support/factories"
import { renderAccount, serveAccount } from "@/test/support/accountDetail"

const dialog = () => screen.getByRole("dialog")

/** Simule une largeur d'écran : `true` = bureau (≥ 640 px). */
function setDesktop(desktop: boolean) {
  const original = window.matchMedia
  window.matchMedia = ((query: string) => ({ ...original(query), matches: desktop && query.includes("min-width") })) as typeof window.matchMedia
  return () => { window.matchMedia = original }
}

async function openNew() {
  const ctx = renderAccount()
  await screen.findByRole("heading", { name: /Compte joint/ })
  await ctx.user.click(screen.getByRole("button", { name: "Nouvelle opération" }))
  return ctx
}

describe("TransactionDialog", () => {
  it("pas de champs Icône (Lucide) ni Couleur : ils ne s'affichent nulle part pour une opération", async () => {
    const backend = serveAccount()
    const { user } = await openNew()
    expect(within(dialog()).queryByLabelText(/Icône/)).not.toBeInTheDocument()
    expect(within(dialog()).queryByLabelText(/Couleur/)).not.toBeInTheDocument()

    await user.type(within(dialog()).getByLabelText("Commerçant / Libellé"), "Café")
    await user.type(within(dialog()).getByLabelText("Montant"), "3")
    await user.click(within(dialog()).getByRole("button", { name: "Enregistrer" }))
    await screen.findByText("Transaction ajoutée")
    expect(backend.writes[0].body).not.toHaveProperty("custom_color")
    expect(backend.writes[0].body).not.toHaveProperty("custom_icon")
  })

  it("montant : placeholder « 0,00 » et saisie avec virgule acceptée", async () => {
    const backend = serveAccount()
    const { user } = await openNew()
    const amount = within(dialog()).getByLabelText("Montant")
    expect(amount).toHaveAttribute("placeholder", "0,00")
    expect(amount).toHaveAttribute("inputmode", "decimal")

    await user.type(within(dialog()).getByLabelText("Commerçant / Libellé"), "Café")
    await user.type(amount, "12,50")
    await user.click(within(dialog()).getByRole("button", { name: "Enregistrer" }))
    await screen.findByText("Transaction ajoutée")
    expect(backend.writes[0].body).toEqual(expect.objectContaining({ amount: 12.5 }))
  })

  it("édition : le montant s'affiche avec une virgule", async () => {
    serveAccount([makeTransaction({ id: 5, merchant: "Boulangerie", amount: 8.4, original_amount: 8.4 })])
    const { user } = renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })
    const row = within(screen.getByRole("table")).getByText("Boulangerie").closest("tr")!
    await user.click(within(row).getByTitle("Actions"))
    await user.click(await screen.findByRole("menuitem", { name: "Modifier" }))
    expect(within(dialog()).getByLabelText("Montant")).toHaveValue("8,4")
  })

  it("catégorie par défaut : « Sans catégorie »", async () => {
    serveAccount()
    await openNew()
    expect(within(dialog()).getByRole("combobox", { name: "Catégorie" })).toHaveTextContent("Sans catégorie")
  })

  it("mobile : aucun champ ne prend le focus à l'ouverture (pas de clavier ni de sélecteur de date)", async () => {
    serveAccount()
    const restore = setDesktop(false)
    try {
      await openNew()
      expect(dialog()).toHaveFocus()
    } finally { restore() }
  })

  it("bureau : le focus initial va sur le libellé, pas sur la date", async () => {
    serveAccount()
    const restore = setDesktop(true)
    try {
      await openNew()
      expect(within(dialog()).getByLabelText("Commerçant / Libellé")).toHaveFocus()
    } finally { restore() }
  })
})
