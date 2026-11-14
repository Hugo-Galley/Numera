/** Compte courant : sélection de transactions, modification groupée et suppression groupée. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { makeAccount, makeCategory, makeTransaction } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import AccountDetail from "@/pages/AccountDetail/index"

type Write = { method: string; path: string; body: unknown }

/** L'ordre des identifiants suit celui de la liste affichée : on le normalise. */
const sortIds = (w: Write): Write => ({ ...w, body: { ...(w.body as { ids: number[] }), ids: [...(w.body as { ids: number[] }).ids].sort() } })

const rows = [
  makeTransaction({ id: 101, account_id: 1, merchant: "Boulangerie", amount: 4.5 }),
  makeTransaction({ id: 102, account_id: 1, merchant: "Cinéma", amount: 12 }),
]

function setup() {
  const writes: Write[] = []
  let loads = 0
  const note = async (request: Request) => {
    const text = await request.text()
    writes.push({ method: request.method, path: new URL(request.url).pathname.replace(/^\/api/, ""), body: text ? JSON.parse(text) : null })
  }
  server.use(
    http.get(apiUrl("/accounts/:id"), () => HttpResponse.json(makeAccount({ id: 1, name: "Compte joint" }))),
    http.get(apiUrl("/transactions/merchants"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    http.get(apiUrl("/transactions"), () => { loads += 1; return HttpResponse.json(rows) }),
    http.get(apiUrl("/analytics/timeseries"), () => HttpResponse.json([])),
    http.get(apiUrl("/categories"), () => HttpResponse.json([makeCategory({ id: 3, name: "Sorties" })])),
    http.get(apiUrl("/tags"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/tags"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/account-flow-summary"), () => HttpResponse.json(null)),
    http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ configured: false, hourly_rate: null, work_hours_per_day: 7 })),
    http.patch(apiUrl("/transactions/bulk"), async ({ request }) => { await note(request); return new HttpResponse(null, { status: 204 }) }),
    http.post(apiUrl("/transactions/bulk-delete"), async ({ request }) => { await note(request); return HttpResponse.json({}) }),
  )
  const view = renderWithProviders(
    <WorkTimeProvider>
      <Routes>
        <Route path="/accounts/:id" element={<AccountDetail />} />
      </Routes>
    </WorkTimeProvider>,
    { route: "/accounts/1", auth: true },
  )
  return { ...view, writes, loads: () => loads }
}

/** Attend que la liste soit chargée (le tableau n'existe qu'après le chargement). */
const ready = async () => { await within(await screen.findByRole("table")).findByText("Boulangerie") }
const table = () => within(screen.getByRole("table"))
const rowBox = (merchant: string) => within(table().getByText(merchant).closest("tr")!).getByRole("checkbox")

describe("Compte courant : sélection groupée", () => {
  it("cocher des lignes affiche la barre d'actions avec leur nombre ; la fermer désélectionne", async () => {
    const { user } = setup()
    await ready()

    await user.click(rowBox("Boulangerie"))
    await user.click(rowBox("Cinéma"))

    expect(screen.getAllByText("2").length).toBeGreaterThan(0)
    await user.click(screen.getByRole("button", { name: "Fermer" }))
    await waitFor(() => expect(rowBox("Boulangerie")).not.toBeChecked())
  })

  it("la case de l'en-tête sélectionne toutes les lignes affichées", async () => {
    const { user } = setup()
    await ready()

    await user.click(table().getByRole("checkbox", { name: "Tout sélectionner" }))

    expect(rowBox("Boulangerie")).toBeChecked()
    expect(rowBox("Cinéma")).toBeChecked()
  })

  it("suppression groupée : confirmation avec le nombre, POST des identifiants, rechargement", async () => {
    const { user, writes, loads } = setup()
    await ready()
    await user.click(table().getByRole("checkbox", { name: "Tout sélectionner" }))
    const before = loads()

    await user.click(screen.getByRole("button", { name: "Supprimer" }))
    const dialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(dialog).toHaveTextContent("Supprimer 2 transactions ?")
    await user.click(within(dialog).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(sortIds(writes[0])).toEqual({ method: "POST", path: "/transactions/bulk-delete", body: { ids: [101, 102] } })
    expect(await screen.findByText("2 transactions supprimées")).toBeInTheDocument()
    await waitFor(() => expect(loads()).toBeGreaterThan(before))
  })

  it("suppression groupée annulée : rien n'est envoyé", async () => {
    const { user, writes } = setup()
    await ready()
    await user.click(rowBox("Boulangerie"))

    await user.click(screen.getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))

    expect(writes).toEqual([])
  })

  it("suppression groupée refusée : message d'erreur", async () => {
    const { user } = setup()
    server.use(http.post(apiUrl("/transactions/bulk-delete"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    await ready()
    await user.click(rowBox("Boulangerie"))

    await user.click(screen.getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Erreur lors de la suppression groupée")).toBeInTheDocument()
  })
})

describe("Compte courant : modification groupée", () => {
  async function openBulkEdit(user: ReturnType<typeof setup>["user"]) {
    await ready()
    await user.click(table().getByRole("checkbox", { name: "Tout sélectionner" }))
    await user.click(screen.getByRole("button", { name: "Modifier" }))
    return screen.findByRole("dialog", { name: "Modification groupée" })
  }

  it("annonce le nombre de transactions concernées", async () => {
    const { user } = setup()

    const dialog = await openBulkEdit(user)

    expect(dialog).toHaveTextContent("Appliquer ces changements aux 2 transactions sélectionnées.")
  })

  it("sans changement choisi : le corps ne contient que les identifiants", async () => {
    const { user, writes } = setup()
    const dialog = await openBulkEdit(user)

    await user.click(within(dialog).getByRole("button", { name: "Appliquer" }))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(sortIds(writes[0])).toEqual({ method: "PATCH", path: "/transactions/bulk", body: { ids: [101, 102] } })
    expect(await screen.findByText("2 transactions mises à jour")).toBeInTheDocument()
  })

  it("catégorie « Aucune » et caractère récurrent : envoyés dans le corps", async () => {
    const { user, writes } = setup()
    const dialog = await openBulkEdit(user)

    const [category, recurring] = within(dialog).getAllByRole("combobox")
    await user.click(category)
    await user.click(await screen.findByRole("option", { name: "Aucune catégorie" }))
    await user.click(recurring)
    await user.click(await screen.findByRole("option", { name: "Récurrente" }))
    await user.click(within(dialog).getByRole("button", { name: "Appliquer" }))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(sortIds(writes[0]).body).toEqual({ ids: [101, 102], category_id: null, is_recurring: true })
  })

  it("catégorie existante : son identifiant part en nombre", async () => {
    const { user, writes } = setup()
    const dialog = await openBulkEdit(user)

    await user.click(within(dialog).getAllByRole("combobox")[0])
    await user.click(await screen.findByRole("option", { name: "Sorties" }))
    await user.click(within(dialog).getByRole("button", { name: "Appliquer" }))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(sortIds(writes[0]).body).toEqual({ ids: [101, 102], category_id: 3 })
  })

  it("modification refusée : message d'erreur, fenêtre conservée", async () => {
    const { user } = setup()
    server.use(http.patch(apiUrl("/transactions/bulk"), () => HttpResponse.json({ detail: "Catégorie interdite" }, { status: 422 })))
    const dialog = await openBulkEdit(user)

    await user.click(within(dialog).getByRole("button", { name: "Appliquer" }))

    expect(await screen.findByText("Catégorie interdite")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Modification groupée" })).toBeInTheDocument()
  })
})
