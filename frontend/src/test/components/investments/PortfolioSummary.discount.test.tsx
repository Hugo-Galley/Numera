/** Résumé du portefeuille : la plus-value latente se détaille en décote d'achat et gain de marché. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { PortfolioSummary } from "@/components/investments/PortfolioSummary"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

const portfolio = (extra: Record<string, unknown>) => ({
  account_id: 5, account_name: "AXA", currency: "EUR", valued_by_positions: true, value_source: "positions",
  baseline_date: null, value: 1500, value_eur: 1500, positions_value_eur: 1500, cash: 0, net_invested: 750, net_invested_eur: 750,
  gain: 750, gain_eur: 750, performance_pct: 100, xirr_pct: null, twr_pct: null, period_days: 30,
  unrealized_eur: 750, unrealized_pct: 100, fx_effect_eur: null, lines_without_cost: [], realized_eur: 0, realized_unknown_sales: 0,
  realized_by_year: [], dividends_eur: 0, dividends_12m_eur: 0, withholding_eur: 0, fees_eur: 0, stale_tickers: [], snapshot: null,
  reconciliation: null, warnings: [], ...extra,
})

describe("PortfolioSummary : décote d'achat", () => {
  it("détaille la plus-value latente en décote et gain de marché", async () => {
    server.use(http.get(apiUrl("/analytics/portfolio/5"), () => HttpResponse.json(portfolio({ discount_eur: 250, market_gain_eur: 500 }))))
    renderWithProviders(<PortfolioSummary accountId={5} />, { route: "/accounts/5", auth: true })

    expect(await screen.findByText(/dont décote \+250,00/)).toBeInTheDocument()
    expect(screen.getByText(/marché \+500,00/)).toBeInTheDocument()
  })

  it("sans cours de référence : aucune mention de décote", async () => {
    server.use(http.get(apiUrl("/analytics/portfolio/5"), () => HttpResponse.json(portfolio({ discount_eur: null, market_gain_eur: null }))))
    renderWithProviders(<PortfolioSummary accountId={5} />, { route: "/accounts/5", auth: true })

    await screen.findByText("Plus-value latente")
    expect(screen.queryByText(/décote/)).not.toBeInTheDocument()
  })
})
