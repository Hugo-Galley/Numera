/** Positions d'un compte titres : filtres, édition du PRU, dividende, suppression, décomposition d'un ETF. */
import { screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import type { PortfolioHolding } from "@/types/diversity"
import { HoldingsTable } from "@/components/investments/HoldingsTable"

const holding = (overrides: Partial<PortfolioHolding> = {}): PortfolioHolding => ({
  id: 1, account_id: 5, ticker: "CW8.PA", isin: "LU1681043599", asset_name: "Amundi MSCI World", quantity: 12.5,
  buy_price_avg: 480, currency: "EUR", current_price: 520.4, current_price_eur: 520.4, current_value_eur: 6505,
  total_invested_eur: 6000, gain_eur: 505, gain_pct: 8.42, is_etf: true, etf_profile_id: 9, ...overrides,
})
const air = holding({ id: 2, ticker: "AI.PA", isin: "FR0000120073", asset_name: "Air Liquide", quantity: 3, is_etf: false, etf_profile_id: undefined, current_value_eur: 540.3, total_invested_eur: 600, gain_eur: -59.7, gain_pct: -9.95, buy_price_avg: 200 })
const world = holding()
/** ETF sans profil de composition : seul cas où « Décomposer en ligne » est proposé. */
const fund = holding({ id: 3, ticker: "0P0001.F", isin: "FR0014001FD5", asset_name: "Fonds Monde", etf_profile_id: undefined, buy_price_avg: 100 })

function setup(holdings = [world, air, fund]) {
  const onRefresh = vi.fn()
  const onAddDividend = vi.fn()
  const view = renderWithProviders(
    <HoldingsTable accountId={5} accountName="PEA" holdings={holdings} onRefresh={onRefresh} onAddDividend={onAddDividend} />,
    { auth: true },
  )
  return { onRefresh, onAddDividend, ...view }
}

/** Les écritures sur /holdings/:id, consignées avec leur corps. */
function serveWrites() {
  const writes: { method: string; path: string; body: unknown }[] = []
  server.use(
    http.put(apiUrl("/holdings/:id"), async ({ request, params }) => { writes.push({ method: "PUT", path: `/holdings/${params.id}`, body: await request.json() }); return HttpResponse.json({}) }),
    http.delete(apiUrl("/holdings/:id"), ({ params }) => { writes.push({ method: "DELETE", path: `/holdings/${params.id}`, body: null }); return new HttpResponse(null, { status: 204 }) }),
  )
  return writes
}

const table = () => within(screen.getByRole("table"))
const rowOf = (name: string) => within(screen.getAllByRole("row").find((r) => within(r).queryByText(name))!)

describe("HoldingsTable : filtres", () => {
  it("la recherche filtre par nom, ticker ou ISIN ; « Réinitialiser » rétablit la liste", async () => {
    const { user } = setup()

    await user.type(screen.getByPlaceholderText("Nom, ticker, ISIN…"), "liquide")
    expect(table().queryByText("Amundi MSCI World")).not.toBeInTheDocument()
    expect(table().getByText("Air Liquide")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: /Réinitialiser/ }))
    expect(table().getByText("Amundi MSCI World")).toBeInTheDocument()
  })

  it("filtre par type : ETF ou actions", async () => {
    const { user } = setup()

    await user.click(screen.getByRole("button", { name: "ETFs" }))
    expect(table().queryByText("Air Liquide")).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Actions" }))
    expect(table().queryByText("Amundi MSCI World")).not.toBeInTheDocument()
    expect(table().getByText("Air Liquide")).toBeInTheDocument()
  })

  it("filtre par performance : en gain ou en perte", async () => {
    const { user } = setup()

    await user.click(screen.getByRole("button", { name: /En perte/ }))
    expect(table().queryByText("Amundi MSCI World")).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /En gain/ }))
    expect(table().queryByText("Air Liquide")).not.toBeInTheDocument()
    expect(table().getByText("Amundi MSCI World")).toBeInTheDocument()
  })

  it("aucun résultat : message et lien de réinitialisation", async () => {
    const { user } = setup()

    await user.type(screen.getByPlaceholderText("Nom, ticker, ISIN…"), "zzz")

    expect(await screen.findByText("Aucune position ne correspond aux filtres")).toBeInTheDocument()
  })

  it("aucune position : invite à définir le Point Zéro", () => {
    setup([])

    expect(screen.getByText("Aucune position active renseignée")).toBeInTheDocument()
  })
})

describe("HoldingsTable : PRU", () => {
  it("modifier le PRU : PUT avec la valeur (virgule acceptée), puis rafraîchissement", async () => {
    const writes = serveWrites()
    const { user, onRefresh } = setup()

    await user.click(rowOf("Air Liquide").getByTitle("Modifier le PRU"))
    const input = table().getByPlaceholderText("PRU (EUR)")
    await user.clear(input)
    await user.type(input, "210,5")
    await user.click(table().getByTitle("Enregistrer"))

    await waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1))
    expect(writes).toEqual([{ method: "PUT", path: "/holdings/2", body: { buy_price_avg: 210.5 } }])
    expect(await screen.findByText("PRU de AI.PA mis à jour")).toBeInTheDocument()
  })

  it("PRU vidé : envoie null (PRU inconnu)", async () => {
    const writes = serveWrites()
    const { user } = setup()

    await user.click(rowOf("Air Liquide").getByTitle("Modifier le PRU"))
    await user.clear(table().getByPlaceholderText("PRU (EUR)"))
    await user.click(table().getByTitle("Enregistrer"))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].body).toEqual({ buy_price_avg: null })
  })

  it("PRU invalide (zéro ou négatif) : message, aucune requête ; annuler referme l'édition", async () => {
    const writes = serveWrites()
    const { user } = setup()

    await user.click(rowOf("Air Liquide").getByTitle("Modifier le PRU"))
    const input = table().getByPlaceholderText("PRU (EUR)")
    await user.clear(input)
    await user.type(input, "0")
    await user.click(table().getByTitle("Enregistrer"))

    expect(await screen.findByText(/Le PRU doit être/)).toBeInTheDocument()
    expect(writes).toEqual([])
    await user.click(table().getByTitle("Annuler"))
    expect(table().queryByPlaceholderText("PRU (EUR)")).not.toBeInTheDocument()
  })

  it("PRU refusé par le serveur : message d'erreur, pas de rafraîchissement", async () => {
    server.use(http.put(apiUrl("/holdings/:id"), () => HttpResponse.json({ detail: "Position verrouillée" }, { status: 400 })))
    const { user, onRefresh } = setup()

    await user.click(rowOf("Air Liquide").getByTitle("Modifier le PRU"))
    await user.click(table().getByTitle("Enregistrer"))

    expect(await screen.findByText("Position verrouillée")).toBeInTheDocument()
    expect(onRefresh).not.toHaveBeenCalled()
  })
})

describe("HoldingsTable : actions sur une position", () => {
  it("titre distribuant : PUT pays_dividends inversé", async () => {
    const writes = serveWrites()
    const { user, onRefresh } = setup()

    await user.click(rowOf("Air Liquide").getByTitle("Marquer comme titre distribuant (rappel de dividende)"))

    await waitFor(() => expect(onRefresh).toHaveBeenCalled())
    expect(writes).toEqual([{ method: "PUT", path: "/holdings/2", body: { pays_dividends: true } }])
  })

  it("« Saisir un dividende » transmet la position", async () => {
    const { user, onAddDividend } = setup()

    await user.click(rowOf("Air Liquide").getByTitle("Saisir un dividende"))

    expect(onAddDividend).toHaveBeenCalledTimes(1)
    expect(onAddDividend.mock.calls[0][0]).toMatchObject({ id: 2, ticker: "AI.PA" })
  })

  it("suppression : confirmation puis DELETE ; refusée, rien n'est envoyé", async () => {
    const writes = serveWrites()
    const { user, onRefresh } = setup()

    await user.click(rowOf("Air Liquide").getByTitle("Supprimer la position"))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))
    expect(writes).toEqual([])

    await user.click(rowOf("Air Liquide").getByTitle("Supprimer la position"))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(onRefresh).toHaveBeenCalled())
    expect(writes).toEqual([{ method: "DELETE", path: "/holdings/2", body: null }])
    expect(await screen.findByText("Position supprimée")).toBeInTheDocument()
  })

  it("décomposer en ligne : profil créé puis rattaché à la position", async () => {
    const writes = serveWrites()
    let decomposed: unknown
    server.use(http.post(apiUrl("/etf-profiles/auto-decompose"), async ({ request }) => { decomposed = await request.json(); return HttpResponse.json({ id: 31, name: "Fonds Monde SA" }) }))
    const { user, onRefresh } = setup()

    await user.click(rowOf("Fonds Monde").getByTitle("Décomposer en ligne"))

    await waitFor(() => expect(onRefresh).toHaveBeenCalled())
    expect(decomposed).toMatchObject({ symbol: "0P0001.F", name: "Fonds Monde", isin: "FR0014001FD5" })
    expect(writes).toEqual([{ method: "PUT", path: "/holdings/3", body: { etf_profile_id: 31 } }])
  })

  it("décomposition sans profil renvoyé : message d'échec, position inchangée", async () => {
    const writes = serveWrites()
    server.use(http.post(apiUrl("/etf-profiles/auto-decompose"), () => HttpResponse.json({})))
    const { user, onRefresh } = setup()

    await user.click(rowOf("Fonds Monde").getByTitle("Décomposer en ligne"))

    expect(await screen.findByText("Impossible de décomposer ce fonds en ligne")).toBeInTheDocument()
    expect(writes).toEqual([])
    expect(onRefresh).not.toHaveBeenCalled()
  })

  it("un ETF déjà décomposé n'a pas de bouton « Décomposer en ligne »", () => {
    setup()

    expect(rowOf("Amundi MSCI World").queryByTitle("Décomposer en ligne")).not.toBeInTheDocument()
  })
})
