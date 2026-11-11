/** Découpage d'une dépense : répartition par catégorie, reste à répartir, validation, annulation du découpage. */
import { screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { SplitTransactionDialog, type SplittableTransaction } from "@/components/transactions/SplitTransactionDialog"

const categories = [
  { id: 1, name: "Courses", type: "depense" },
  { id: 2, name: "Maison", type: "depense" },
  { id: 3, name: "Salaire", type: "revenu" },
  { id: 4, name: "Investissement", type: "depense" },
  { id: 5, name: "Epargne", type: "depense" },
]
const tx: SplittableTransaction = { id: 11, merchant: "Carrefour", amount: 100, currency: "EUR", category_id: 1 }

function setup(transaction: SplittableTransaction | null = tx) {
  const onOpenChange = vi.fn()
  const onDone = vi.fn()
  const view = renderWithProviders(
    <SplitTransactionDialog open onOpenChange={onOpenChange} transaction={transaction} categories={categories} onDone={onDone} />,
    { auth: true },
  )
  return { onOpenChange, onDone, ...view }
}

const amountInputs = () => screen.getAllByPlaceholderText("0,00")
const save = () => screen.getByRole("button", { name: "Enregistrer" })

describe("SplitTransactionDialog", () => {
  it("part de deux lignes : la première reprend la catégorie et le montant, la seconde est vide", () => {
    setup()

    expect(screen.getByRole("dialog")).toHaveTextContent("Carrefour · 100,00")
    const [first, second] = amountInputs()
    expect(first).toHaveValue("100")
    expect(second).toHaveValue("")
    expect(screen.getAllByRole("combobox")[0]).toHaveTextContent("Courses")
    expect(save()).toBeDisabled()
  })

  it("reste à répartir : suit la saisie, « Montant réparti » quand le total est atteint", async () => {
    const { user } = setup()
    const [first, second] = amountInputs()

    await user.clear(first)
    await user.type(first, "60")
    expect(screen.getByText(/Reste 40,00/)).toBeInTheDocument()

    await user.type(second, "40")
    expect(screen.getByText("Montant réparti")).toBeInTheDocument()
  })

  it("double-clic sur un montant : y reporte le reste (virgule acceptée)", async () => {
    const { user } = setup()
    const [first, second] = amountInputs()
    await user.clear(first)
    await user.type(first, "33,5")

    await user.dblClick(second)

    expect(second).toHaveValue("66.50")
    expect(screen.getByText("Montant réparti")).toBeInTheDocument()
  })

  it("on ne propose ni revenu, ni Investissement, ni Epargne comme catégorie d'une part", async () => {
    const { user } = setup()

    await user.click(screen.getAllByRole("combobox")[1])

    const options = (await screen.findAllByRole("option")).map((o) => o.textContent)
    expect(options).toEqual(["Courses", "Maison"])
  })

  it("ajouter / retirer une part : jamais moins de deux lignes", async () => {
    const { user } = setup()
    const remove = () => screen.getAllByTitle("Retirer la part")
    expect(remove()[0]).toBeDisabled()

    await user.click(screen.getByRole("button", { name: "Ajouter une part" }))
    expect(amountInputs()).toHaveLength(3)
    await user.click(remove()[2])

    expect(amountInputs()).toHaveLength(2)
    expect(remove()[0]).toBeDisabled()
  })

  it("enregistre : PUT des parts (catégorie et montant numériques), message, fermeture, onDone", async () => {
    let body: unknown
    server.use(http.put(apiUrl("/transactions/11/splits"), async ({ request }) => { body = await request.json(); return HttpResponse.json({}) }))
    const { user, onOpenChange, onDone } = setup()
    const [first, second] = amountInputs()
    await user.clear(first)
    await user.type(first, "70,25")
    await user.click(screen.getAllByRole("combobox")[1])
    await user.click(await screen.findByRole("option", { name: "Maison" }))
    await user.type(second, "29,75")
    expect(save()).toBeEnabled()

    await user.click(save())

    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1))
    expect(body).toEqual({ items: [{ category_id: 1, amount: 70.25 }, { category_id: 2, amount: 29.75 }] })
    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(await screen.findByText("Dépense découpée")).toBeInTheDocument()
  })

  it("« Enregistrer » reste désactivé si une part n'a pas de catégorie ou si le total n'y est pas", async () => {
    const { user } = setup()
    const [first, second] = amountInputs()
    await user.clear(first)
    await user.type(first, "60")
    await user.type(second, "40")
    // Total atteint mais seconde part sans catégorie
    expect(save()).toBeDisabled()

    await user.click(screen.getAllByRole("combobox")[1])
    await user.click(await screen.findByRole("option", { name: "Maison" }))
    expect(save()).toBeEnabled()

    await user.clear(second)
    await user.type(second, "39")
    expect(save()).toBeDisabled()
  })

  it("échec de l'enregistrement : message du serveur, fenêtre ouverte", async () => {
    server.use(http.put(apiUrl("/transactions/11/splits"), () => HttpResponse.json({ detail: "Catégorie interdite" }, { status: 422 })))
    const { user, onDone, onOpenChange } = setup({ ...tx, splits: [{ category_id: 1, amount: 60 }, { category_id: 2, amount: 40 }] })

    await user.click(save())

    expect(await screen.findByText("Catégorie interdite")).toBeInTheDocument()
    expect(onDone).not.toHaveBeenCalled()
    expect(onOpenChange).not.toHaveBeenCalled()
  })

  it("découpage existant : parts préremplies et « Annuler le découpage » envoie une liste vide", async () => {
    let body: unknown
    server.use(http.put(apiUrl("/transactions/11/splits"), async ({ request }) => { body = await request.json(); return HttpResponse.json({}) }))
    const { user, onDone } = setup({ ...tx, splits: [{ category_id: 1, amount: 60 }, { category_id: 2, amount: 40 }] })
    expect(amountInputs().map((i) => (i as HTMLInputElement).value)).toEqual(["60", "40"])

    await user.click(screen.getByRole("button", { name: "Annuler le découpage" }))

    await waitFor(() => expect(onDone).toHaveBeenCalled())
    expect(body).toEqual({ items: [] })
    expect(await screen.findByText("Découpage annulé")).toBeInTheDocument()
  })

  it("sans découpage existant : pas de bouton « Annuler le découpage » ; « Fermer » ferme", async () => {
    const { user, onOpenChange } = setup()
    expect(screen.queryByRole("button", { name: "Annuler le découpage" })).not.toBeInTheDocument()

    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Fermer" }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
