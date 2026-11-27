/** Répartition d'un compte : charge le scanner du seul compte, gère le vide et l'échec. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { AccountBreakdown } from "@/components/investments/AccountBreakdown"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

const scanner = (stocks: number) => ({
  score: 70, score_label: "Bonne",
  totals: { stocks_eur: stocks, direct_eur: stocks, etf_eur: 0, epargne_eur: 0, courant_eur: 0, fonds_euros_eur: 0, other_eur: 0, wealth_eur: stocks, holdings_count: 1, etfs_count: 0 },
  top_underlying_companies: stocks ? [{ name: "Apple Inc.", ticker: "AAPL", direct_value_eur: stocks, indirect_value_eur: 0, total_value_eur: stocks, pct_stocks: 100, pct_total_wealth: 100, sources: [], has_overlap: false }] : [],
  countries: [], sectors: [], alerts: [], etf_compositions: [],
  holdings: stocks ? [{ id: 1, account_id: 4, ticker: "AAPL", isin: null, name: "Apple", quantity: 1, price_eur: stocks, value_eur: stocks, etf_profile_id: null, is_etf: false }] : [],
})

describe("AccountBreakdown", () => {
  it("demande la répartition du seul compte", async () => {
    const seen: string[] = []
    server.use(http.get(apiUrl("/analytics/diversity-scanner"), ({ request }) => {
      seen.push(new URL(request.url).search)
      return HttpResponse.json(scanner(1000))
    }))
    renderWithProviders(<AccountBreakdown accountId={4} />, { route: "/accounts/4", auth: true })

    expect(await screen.findByText("Répartition du compte")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
    expect(seen).toEqual(["?account_id=4"])
  })

  it("sans position valorisée : rien n'est affiché", async () => {
    let calls = 0
    server.use(http.get(apiUrl("/analytics/diversity-scanner"), () => { calls += 1; return HttpResponse.json(scanner(0)) }))
    const { container } = renderWithProviders(<AccountBreakdown accountId={4} />, { route: "/accounts/4", auth: true })

    await vi.waitFor(() => expect(calls).toBe(1))
    await vi.waitFor(() => expect(container.querySelector(".animate-pulse")).toBeNull())
    expect(screen.queryByText("Répartition du compte")).not.toBeInTheDocument()
  })

  it("un échec se distingue d'une absence de données et se relance", async () => {
    let calls = 0
    server.use(http.get(apiUrl("/analytics/diversity-scanner"), () => {
      calls += 1
      return calls === 1 ? HttpResponse.json({ detail: "boom" }, { status: 500 }) : HttpResponse.json(scanner(1000))
    }))
    const { user } = renderWithProviders(<AccountBreakdown accountId={4} />, { route: "/accounts/4", auth: true })

    expect(await screen.findByText("Impossible de calculer la répartition du compte")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Réessayer" }))
    expect(await screen.findByText("Apple Inc.")).toBeInTheDocument()
  })
})
