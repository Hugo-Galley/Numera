/** Carte « Répartition du compte » : donut par entreprise (ETF décomposés), vues, zoom et erreurs. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { AccountBreakdown } from "@/components/investments/AccountBreakdown"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

const company = (name: string, ticker: string, value: number) => ({
  name, ticker, direct_value_eur: value, indirect_value_eur: 0, total_value_eur: value,
  pct_stocks: value / 10, pct_total_wealth: 0, sources: [], has_overlap: false,
})
const holding = (id: number, ticker: string, name: string, value: number, isEtf = false) => ({
  id, account_id: 4, ticker, isin: null, name, quantity: 1, price_eur: value, value_eur: value, etf_profile_id: isEtf ? 1 : null, is_etf: isEtf,
})
const scanner = (extra: Record<string, unknown> = {}) => ({
  score: 70, score_label: "Bonne",
  totals: { stocks_eur: 1000, epargne_eur: 0, courant_eur: 0, fonds_euros_eur: 0, other_eur: 0, wealth_eur: 1000, holdings_count: 3, etfs_count: 1 },
  top_underlying_companies: [company("Apple Inc.", "AAPL", 300), company("TotalEnergies SE", "TTE", 200), company("BlackRock, Inc.", "BLK", 150)],
  countries: [{ name: "USA", value_eur: 600, percentage_stocks: 60, percentage_total_wealth: 60 }],
  sectors: [{ name: "Technologie", value_eur: 500, percentage_stocks: 50, percentage_total_wealth: 50 }],
  alerts: [],
  holdings: [holding(1, "AAPL", "Apple", 300), holding(2, "TTE", "Total", 200), holding(3, "CW8", "MSCI World", 500, true)],
  etf_compositions: [],
  ...extra,
})

function serve(body: Record<string, unknown>, seen: string[] = []) {
  server.use(http.get(apiUrl("/analytics/diversity-scanner"), ({ request }) => {
    seen.push(new URL(request.url).search)
    return HttpResponse.json(body)
  }))
}

describe("AccountBreakdown", () => {
  it("demande la répartition du compte et liste les entreprises avec « Autres » pour le reste", async () => {
    const seen: string[] = []
    serve(scanner(), seen)
    renderWithProviders(<AccountBreakdown accountId={4} />, { route: "/accounts/4", auth: true })

    expect(await screen.findByText("Répartition du compte")).toBeInTheDocument()
    expect(seen).toEqual(["?account_id=4"])
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
    expect(screen.getByText("BlackRock, Inc.")).toBeInTheDocument()
    // 1 000 − 650 de sociétés nommées
    expect(screen.getByText("Autres entreprises")).toBeInTheDocument()
    expect(screen.getByText(/350,00/)).toBeInTheDocument()
    expect(screen.getByText("Valeur des positions")).toBeInTheDocument()
  })

  it("passe aux positions et, en zoom, masque « Autres »", async () => {
    serve(scanner())
    const { user } = renderWithProviders(<AccountBreakdown accountId={4} />, { route: "/accounts/4", auth: true })

    await user.click(await screen.findByRole("button", { name: "Positions" }))
    expect(screen.getByText("MSCI World")).toBeInTheDocument()
    expect(screen.queryByText("Autres positions")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Pays" }))
    expect(screen.getByText("États-Unis")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Entreprises" }))
    await user.click(screen.getByRole("checkbox", { name: /Zoomer sur les lignes nommées/ }))
    expect(screen.queryByText("Autres entreprises")).not.toBeInTheDocument()
    expect(screen.getByText("Lignes nommées")).toBeInTheDocument()
  })

  it("compte crypto sans ETF : ni secteurs ni pays", async () => {
    serve(scanner({
      totals: { stocks_eur: 500, epargne_eur: 0, courant_eur: 0, fonds_euros_eur: 0, other_eur: 0, wealth_eur: 500, holdings_count: 2, etfs_count: 0 },
      top_underlying_companies: [company("Ethereum USD", "ETH-USD", 300), company("Bitcoin USD", "BTC-USD", 200)],
      holdings: [holding(1, "ETH-USD", "Ethereum", 300), holding(2, "BTC-USD", "Bitcoin", 200)],
    }))
    renderWithProviders(<AccountBreakdown accountId={8} />, { route: "/accounts/8", auth: true })

    expect(await screen.findByText("Ethereum USD")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Secteurs" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Pays" })).not.toBeInTheDocument()
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument()
  })

  it("sans position valorisée : rien n'est affiché", async () => {
    const empty = { stocks_eur: 0, epargne_eur: 0, courant_eur: 0, fonds_euros_eur: 0, other_eur: 0, wealth_eur: 0, holdings_count: 0, etfs_count: 0 }
    const seen: string[] = []
    serve(scanner({ totals: empty, top_underlying_companies: [], holdings: [] }), seen)
    const { container } = renderWithProviders(<AccountBreakdown accountId={4} />, { route: "/accounts/4", auth: true })

    await vi.waitFor(() => expect(seen).toHaveLength(1))
    await vi.waitFor(() => expect(container.querySelector(".animate-pulse")).toBeNull())
    expect(screen.queryByText("Répartition du compte")).not.toBeInTheDocument()
  })

  it("un échec se distingue d'une absence de données et se relance", async () => {
    let calls = 0
    server.use(http.get(apiUrl("/analytics/diversity-scanner"), () => {
      calls += 1
      return calls === 1 ? HttpResponse.json({ detail: "boom" }, { status: 500 }) : HttpResponse.json(scanner())
    }))
    const { user } = renderWithProviders(<AccountBreakdown accountId={4} />, { route: "/accounts/4", auth: true })

    expect(await screen.findByText("Impossible de calculer la répartition du compte")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Réessayer" }))
    expect(await screen.findByText("Apple Inc.")).toBeInTheDocument()
  })
})
