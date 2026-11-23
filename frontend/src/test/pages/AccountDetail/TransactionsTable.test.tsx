/** Table et cartes des transactions : nom accessible des cases, icônes de catégorie, tags lisibles (audit visuel). */
import { screen, within } from "@testing-library/react"
import { makeCategory, makeTransaction } from "@/test/support/factories"
import { renderAccount, serveAccount } from "@/test/support/accountDetail"

const monoprix = () => makeTransaction({
  id: 5,
  merchant: "Monoprix",
  date: "2026-11-21T10:00:00",
  category_id: 3,
  category: makeCategory({ id: 3, name: "Courses", color: undefined, icon: undefined }),
  tags: [{ id: 1, name: "Vacances", color: null }],
})

describe("TransactionsTable / TransactionsMobileList", () => {
  it("chaque case de sélection d'une ligne a un nom accessible (libellé et date)", async () => {
    serveAccount([monoprix()])
    renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })
    const boxes = screen.getAllByRole("checkbox", { name: "Sélectionner l'opération Monoprix du 21/11/2026" })
    expect(boxes).toHaveLength(2) // table de bureau + carte mobile
  })

  it("catégorie sans couleur : pastille au fond neutre du thème, pas de blanc en dur", async () => {
    serveAccount([monoprix()])
    renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })
    const cell = within(screen.getByRole("table")).getByText("Courses").closest("td")!
    const chip = cell.querySelector("svg")!.parentElement!
    expect(chip.style.backgroundColor).toBe("")
    expect(chip).toHaveClass("bg-slate-100")
  })

  it("tags : au moins 10 px (plus de texte à 8 px)", async () => {
    serveAccount([monoprix()])
    renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })
    for (const tag of screen.getAllByText("Vacances")) {
      expect(tag.className).not.toMatch(/text-\[(8|9)px\]/)
    }
  })

  it("mobile : la case de sélection a une zone tactile de 44 px", async () => {
    serveAccount([monoprix()])
    renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })
    const boxes = screen.getAllByRole("checkbox", { name: "Sélectionner l'opération Monoprix du 21/11/2026" })
    const mobileBox = boxes.find((b) => !b.closest("table"))!
    expect(mobileBox.closest("label")).toHaveClass("size-11")
  })

  it("mobile : le solde reste à droite de la ligne date / catégorie (pas de retour à la ligne)", async () => {
    serveAccount([monoprix()])
    renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })
    const balance = screen.getByText(/^Solde .*€/)
    expect(balance.parentElement).not.toHaveClass("flex-wrap")
    expect(balance).toHaveClass("shrink-0")
  })
})
