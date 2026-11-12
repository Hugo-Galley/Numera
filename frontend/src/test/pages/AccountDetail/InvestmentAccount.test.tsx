/** Compte titres : mode de valorisation, historique des flux, snapshots de valorisation et nouveau point zéro. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import AccountDetail from "@/pages/AccountDetail/index"

type Write = { method: string; path: string; body: unknown }

const flow = { id: 41, date: "2026-05-03T10:00:00", type: "versement", amount: 500, currency: "EUR", note: "Versement mensuel", ticker: null }
const dividend = { id: 42, date: "2026-05-20T10:00:00", type: "dividende", amount: 12, currency: "EUR", note: "Dividende Air Liquide", ticker: "AI.PA", quantity: null }
const snapshot = { id: 7, date: "2026-05-31T00:00:00", current_value: 10250.5, note: "Point mensuel", is_zero_point: false }
const holding = { id: 1, account_id: 5, ticker: "AI.PA", isin: "FR0000120073", asset_name: "Air Liquide", quantity: 3, buy_price_avg: 150, currency: "EUR", current_price: 160, current_price_eur: 160, current_value_eur: 480, total_invested_eur: 450, gain_eur: 30, gain_pct: 6.6, is_etf: false }

/** Compte titres n° 5 ; les écritures sont consignées et l'analyse rechargée à chaque lecture. */
function setup({ valuationMode = "positions" as string, holdings = [] as object[] } = {}) {
  const writes: Write[] = []
  let analyses = 0
  const note = async (request: Request, path: string) => {
    const text = await request.text()
    writes.push({ method: request.method, path, body: text ? JSON.parse(text) : null })
  }
  server.use(
    http.get(apiUrl("/accounts/5"), () => HttpResponse.json({ ...makeAccount({ id: 5, name: "PEA Boursorama", type: "investissement" }), valuation_mode: valuationMode })),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
    http.get(apiUrl("/transactions/merchants"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    http.get(apiUrl("/analytics/investments/5"), () => { analyses += 1; return HttpResponse.json({ totals: {}, transactions: [flow, dividend], value_series: [snapshot] }) }),
    http.get(apiUrl("/analytics/investments/5/performance-history"), () => HttpResponse.json({ items: [] })),
    http.get(apiUrl("/holdings"), () => HttpResponse.json(holdings)),
    http.get(apiUrl("/analytics/portfolio/5"), () => HttpResponse.json(null)),
    http.get(apiUrl("/analytics/dividends"), () => HttpResponse.json(null)),
    http.get(apiUrl("/analytics/account-flow-summary"), () => HttpResponse.json(null)),
    http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ configured: false, hourly_rate: null, work_hours_per_day: 7 })),
    http.get(apiUrl("/market/validate"), () => HttpResponse.json({ valid: true, symbol: "AI.PA", name: "Air Liquide", price_eur: 160 })),
    http.patch(apiUrl("/accounts/:id"), async ({ request, params }) => { await note(request, `/accounts/${params.id}`); return HttpResponse.json({}) }),
    http.patch(apiUrl("/investment-transactions/:id"), async ({ request, params }) => { await note(request, `/investment-transactions/${params.id}`); return HttpResponse.json({}) }),
    http.delete(apiUrl("/investment-transactions/:id"), async ({ request, params }) => { await note(request, `/investment-transactions/${params.id}`); return new HttpResponse(null, { status: 204 }) }),
    http.post(apiUrl("/balance-snapshots/set-zero-point"), async ({ request }) => { await note(request, "/balance-snapshots/set-zero-point"); return HttpResponse.json({}) }),
    http.post(apiUrl("/balance-snapshots"), async ({ request }) => { await note(request, "/balance-snapshots"); return HttpResponse.json({}) }),
    http.patch(apiUrl("/balance-snapshots/:id"), async ({ request, params }) => { await note(request, `/balance-snapshots/${params.id}`); return HttpResponse.json({}) }),
    http.delete(apiUrl("/balance-snapshots/:id"), async ({ request, params }) => { await note(request, `/balance-snapshots/${params.id}`); return new HttpResponse(null, { status: 204 }) }),
  )
  const view = renderWithProviders(
    <WorkTimeProvider>
      <Routes>
        <Route path="/accounts/:id" element={<AccountDetail />} />
      </Routes>
    </WorkTimeProvider>,
    { route: "/accounts/5", auth: true },
  )
  return { ...view, writes, analyses: () => analyses }
}

type View = ReturnType<typeof setup>
/** Les flux sont rendus en cartes mobiles et en tableau : on cible la ligne du tableau. */
const flowRow = (label: string) => within(screen.getAllByRole("row").find((r) => within(r).queryByText(label))!)
const snapshotRow = () => within(screen.getAllByRole("row").find((r) => within(r).queryByText(/10\s250,50/))!)

describe("Compte titres : valorisation", () => {
  it("passer aux relevés : PATCH valuation_mode puis rechargement ; le mode actif est sans effet", async () => {
    const { user, writes, analyses } = setup()
    await screen.findByRole("heading", { name: /PEA Boursorama/ })
    const before = analyses()

    await user.click(screen.getByRole("button", { name: "Positions × cours" }))
    expect(writes).toEqual([])
    await user.click(screen.getByRole("button", { name: "Relevés" }))

    await waitFor(() => expect(writes).toEqual([{ method: "PATCH", path: "/accounts/5", body: { valuation_mode: "snapshot" } }]))
    expect(await screen.findByText("Valorisation par relevés")).toBeInTheDocument()
    await waitFor(() => expect(analyses()).toBeGreaterThan(before))
  })

  it("changement refusé : message d'erreur", async () => {
    const { user } = setup()
    server.use(http.patch(apiUrl("/accounts/:id"), () => HttpResponse.json({ detail: "Compte verrouillé" }, { status: 400 })))
    await screen.findByRole("heading", { name: /PEA Boursorama/ })

    await user.click(screen.getByRole("button", { name: "Relevés" }))

    expect(await screen.findByText("Compte verrouillé")).toBeInTheDocument()
  })
})

describe("Compte titres : historique des flux", () => {
  it("liste les flux avec leur type, libellé et titre", async () => {
    setup()

    expect(await screen.findAllByText("Versement mensuel")).not.toHaveLength(0)
    expect(screen.getAllByText("Dividende Air Liquide").length).toBeGreaterThan(0)
    expect(screen.getAllByText("AI.PA").length).toBeGreaterThan(0)
  })

  it("suppression d'un flux : confirmation, DELETE, rechargement ; refusée, rien n'est envoyé", async () => {
    const { user, writes, analyses } = setup()
    await screen.findAllByText("Versement mensuel")
    const before = analyses()

    await user.click(flowRow("Versement mensuel").getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))
    expect(writes).toEqual([])

    await user.click(flowRow("Versement mensuel").getByRole("button", { name: "Supprimer" }))
    const dialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(dialog).toHaveTextContent("Supprimer ce flux ?")
    await user.click(within(dialog).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "DELETE", path: "/investment-transactions/41", body: null }]))
    expect(await screen.findByText("Flux supprimé")).toBeInTheDocument()
    await waitFor(() => expect(analyses()).toBeGreaterThan(before))
  })

  it("suppression refusée : message d'erreur", async () => {
    const { user } = setup()
    server.use(http.delete(apiUrl("/investment-transactions/:id"), () => HttpResponse.json({ detail: "Flux rapproché" }, { status: 409 })))
    await screen.findAllByText("Versement mensuel")

    await user.click(flowRow("Versement mensuel").getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Flux rapproché")).toBeInTheDocument()
  })

  it("modification : le dialogue est prérempli, PATCH au lieu d'un POST", async () => {
    const { user, writes } = setup()
    await screen.findAllByText("Versement mensuel")

    await user.click(flowRow("Versement mensuel").getByRole("button", { name: "Modifier" }))
    const dialog = await screen.findByRole("dialog", { name: "Modifier le flux" })
    expect(within(dialog).getByDisplayValue("500")).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue("Versement mensuel")).toBeInTheDocument()
    const amount = within(dialog).getByDisplayValue("500")
    await user.clear(amount)
    await user.type(amount, "600")
    await user.click(within(dialog).getByRole("button", { name: "Confirmer" }))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0]).toMatchObject({ method: "PATCH", path: "/investment-transactions/41", body: { account_id: 5, type: "versement", amount: 600, note: "Versement mensuel" } })
    expect(await screen.findByText("Opération modifiée")).toBeInTheDocument()
  })

  it("« Dividende » d'une position : ouvre le flux prérempli avec le titre", async () => {
    const { user } = setup({ holdings: [holding] })

    await user.click(await screen.findByTitle("Saisir un dividende"))

    const dialog = await screen.findByRole("dialog", { name: "Flux d'investissement" })
    expect(within(dialog).getByDisplayValue("AI.PA")).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue("Dividende Air Liquide")).toBeInTheDocument()
  })
})

describe("Compte titres : snapshots", () => {
  async function openSnapshotDialog(view: View) {
    await view.user.click(await screen.findByRole("button", { name: "Nouveau Snapshot" }))
    return screen.getByRole("dialog", { name: "Mettre à jour la valeur" })
  }

  it("liste les snapshots (date, valeur)", async () => {
    setup()

    expect((await screen.findAllByText(/10\s250,50/)).length).toBeGreaterThan(0)
    expect(screen.getByText("Derniers Snapshots")).toBeInTheDocument()
  })

  it("valeur absente ou négative : message, aucune requête", async () => {
    const view = setup()
    const dialog = await openSnapshotDialog(view)

    await view.user.click(within(dialog).getByRole("button", { name: "Mettre à jour" }))
    expect(await screen.findByText("Saisissez une valeur valide (nombre positif ou nul)")).toBeInTheDocument()
    await view.user.type(within(dialog).getByLabelText(/Valeur Actuelle/), "-5")
    await view.user.click(within(dialog).getByRole("button", { name: "Mettre à jour" }))

    expect(view.writes).toEqual([])
  })

  it("création : POST avec compte, date, valeur et note, puis fermeture et rechargement", async () => {
    const view = setup()
    const before = view.analyses()
    const dialog = await openSnapshotDialog(view)

    fireDate(within(dialog).getByLabelText("Date"), "2026-06-30")
    await view.user.type(within(dialog).getByLabelText(/Valeur Actuelle/), "11000")
    await view.user.type(within(dialog).getByLabelText("Note (Optionnel)"), "Fin de mois")
    await view.user.click(within(dialog).getByRole("button", { name: "Mettre à jour" }))

    await waitFor(() => expect(view.writes).toEqual([{ method: "POST", path: "/balance-snapshots", body: { account_id: 5, date: "2026-06-30", current_value: 11000, note: "Fin de mois", is_zero_point: false } }]))
    expect(await screen.findByText("Snapshot enregistré")).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Mettre à jour la valeur" })).not.toBeInTheDocument())
    expect(view.analyses()).toBeGreaterThan(before)
  })

  it("modification : prérempli, PATCH du snapshot", async () => {
    const { user, writes } = setup()
    await screen.findAllByText(/10\s250,50/)

    await user.click(snapshotRow().getByRole("button", { name: "Modifier" }))
    const dialog = await screen.findByRole("dialog", { name: "Modifier le snapshot" })
    const value = within(dialog).getByDisplayValue("10250.5")
    await user.clear(value)
    await user.type(value, "10300")
    await user.click(within(dialog).getByRole("button", { name: "Mettre à jour" }))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0]).toMatchObject({ method: "PATCH", path: "/balance-snapshots/7", body: { account_id: 5, date: "2026-05-31", current_value: 10300, note: "Point mensuel" } })
    expect(await screen.findByText("Snapshot modifié")).toBeInTheDocument()
  })

  it("suppression confirmée : DELETE puis message", async () => {
    const { user, writes } = setup()
    await screen.findAllByText(/10\s250,50/)

    await user.click(snapshotRow().getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "DELETE", path: "/balance-snapshots/7", body: null }]))
    expect(await screen.findByText("Snapshot supprimé")).toBeInTheDocument()
  })

  it("enregistrement refusé : message du serveur, dialogue ouvert", async () => {
    const view = setup()
    server.use(http.post(apiUrl("/balance-snapshots"), () => HttpResponse.json({ detail: "Date déjà utilisée" }, { status: 409 })))
    const dialog = await openSnapshotDialog(view)

    await view.user.type(within(dialog).getByLabelText(/Valeur Actuelle/), "11000")
    await view.user.click(within(dialog).getByRole("button", { name: "Mettre à jour" }))

    expect(await screen.findByText("Date déjà utilisée")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Mettre à jour la valeur" })).toBeInTheDocument()
  })
})

describe("Compte titres : nouveau point zéro", () => {
  async function openZero(view: View) {
    await view.user.click(await screen.findByRole("button", { name: "Nouveau point zéro" }))
    return screen.getByRole("dialog", { name: "Nouveau point zéro" })
  }

  it("valeur invalide : message, aucune requête", async () => {
    const view = setup()
    const dialog = await openZero(view)

    await view.user.click(within(dialog).getByRole("button", { name: "Réinitialiser la base" }))

    expect(await screen.findByText("Saisissez une valeur d'ouverture valide (nombre positif ou nul)")).toBeInTheDocument()
    expect(view.writes).toEqual([])
  })

  it("valeur saisie : POST set-zero-point (date naïve), fermeture, rechargement", async () => {
    const view = setup()
    const before = view.analyses()
    const dialog = await openZero(view)

    fireDate(within(dialog).getByLabelText("Date d'effet"), "2026-01-01")
    await view.user.type(within(dialog).getByLabelText(/Valeur de référence/), "9000")
    await view.user.type(within(dialog).getByLabelText("Motif du reset"), "Début d'année")
    await view.user.click(within(dialog).getByRole("button", { name: "Réinitialiser la base" }))

    await waitFor(() => expect(view.writes).toEqual([{ method: "POST", path: "/balance-snapshots/set-zero-point", body: { account_id: 5, date: "2026-01-01T00:00:00", current_value: 9000, note: "Début d'année" } }]))
    expect(await screen.findByText("Nouveau point zéro défini")).toBeInTheDocument()
    await waitFor(() => expect(view.analyses()).toBeGreaterThan(before))
  })

  it("refus du serveur : message d'erreur", async () => {
    const view = setup()
    server.use(http.post(apiUrl("/balance-snapshots/set-zero-point"), () => HttpResponse.json({ detail: "Point zéro verrouillé" }, { status: 409 })))
    const dialog = await openZero(view)

    await view.user.type(within(dialog).getByLabelText(/Valeur de référence/), "9000")
    await view.user.click(within(dialog).getByRole("button", { name: "Réinitialiser la base" }))

    expect(await screen.findByText("Point zéro verrouillé")).toBeInTheDocument()
  })
})

/** Un champ date se renseigne d'un coup : `userEvent.type` ne sait pas saisir dans `type="date"`. */
import { fireEvent } from "@testing-library/react"
function fireDate(input: HTMLElement, value: string) {
  fireEvent.change(input, { target: { value } })
}
