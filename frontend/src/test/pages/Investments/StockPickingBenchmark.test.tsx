/** Page Investissements : stock picking face à l'indice de référence (portefeuille fantôme calculé par le backend). */
import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { StockPickingBenchmark } from "@/pages/Investments/StockPickingBenchmark"

const line = {
  ticker: "AAPL", asset_name: "Apple", account_id: 7, account_name: "CTO", missing_price: false, start_date: "2026-01-05",
  invested_eur: 1000, stock_total_eur: 1370, benchmark_total_eur: 1150, gap_eur: 220, stock_xirr_pct: 61.2, benchmark_xirr_pct: 24.5,
}
const body = (extra: Record<string, unknown> = {}) => ({
  account_id: null, benchmark_ticker: "CW8.PA", benchmark_name: "MSCI World", benchmark_source: "largest_etf", benchmark_distributes: false,
  candidates: [{ ticker: "CW8.PA", name: "MSCI World" }], start_date: "2026-01-05", invested_eur: 1000, stock_total_eur: 1370,
  benchmark_total_eur: 1150, gap_eur: 220, stock_xirr_pct: 61.2, benchmark_xirr_pct: 24.5, incomplete_tickers: [], warnings: [],
  lines: [line], ...extra,
})

describe("Investissements : stock picking vs référence", () => {
  it("affiche l'écart, les rendements des deux côtés et le tableau par action", async () => {
    server.use(http.get(apiUrl("/analytics/stock-picking-benchmark"), () => HttpResponse.json(body())))
    renderWithProviders(<StockPickingBenchmark />, { route: "/investments", auth: true })

    expect(await screen.findByRole("heading", { name: "Stock picking vs MSCI World" })).toBeInTheDocument()
    expect(screen.getAllByText(/\+\s?220,00/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/61,2/).length).toBeGreaterThan(0)
    const row = screen.getByRole("row", { name: /Apple/ })
    expect(within(row).getByText(/1\s?150,00/)).toBeInTheDocument()
  })

  it("marque une ligne au cours manquant et affiche les avertissements", async () => {
    server.use(http.get(apiUrl("/analytics/stock-picking-benchmark"), () => HttpResponse.json(body({
      lines: [{ ...line, missing_price: true, gap_eur: null, benchmark_total_eur: null }],
      warnings: ["Cours ou montant manquant pour AAPL : lignes exclues des totaux."],
    }))))
    renderWithProviders(<StockPickingBenchmark />, { route: "/investments", auth: true })

    expect(await screen.findByText("Cours manquant")).toBeInTheDocument()
    expect(screen.getByText(/lignes exclues des totaux/)).toBeInTheDocument()
  })

  it("un autre ticker saisi est enregistré comme référence puis la comparaison est relue", async () => {
    let saved: { ticker: string | null } | null = null
    server.use(
      http.get(apiUrl("/analytics/stock-picking-benchmark"), () =>
        HttpResponse.json(saved ? body({ benchmark_ticker: "IWDA.AS", benchmark_name: "IWDA.AS", benchmark_source: "setting" }) : body())),
      http.put(apiUrl("/analytics/stock-picking-benchmark/reference"), async ({ request }) => {
        saved = (await request.json()) as { ticker: string | null }
        return HttpResponse.json(saved)
      }),
    )
    const { user } = renderWithProviders(<StockPickingBenchmark />, { route: "/investments", auth: true })

    await user.type(await screen.findByRole("textbox", { name: "Autre ticker" }), "IWDA.AS")
    await user.click(screen.getByRole("button", { name: "Appliquer" }))

    expect(await screen.findByRole("heading", { name: "Stock picking vs IWDA.AS" })).toBeInTheDocument()
    expect(saved).toEqual({ ticker: "IWDA.AS" })
  })
})

describe("Investissements : stock picking sans action", () => {
  it("n'affiche pas de totaux à zéro, seulement l'état vide", async () => {
    server.use(http.get(apiUrl("/analytics/stock-picking-benchmark"), () =>
      HttpResponse.json(body({ lines: [], start_date: null, gap_eur: 0, stock_total_eur: 0, benchmark_total_eur: 0 }))))
    renderWithProviders(<StockPickingBenchmark />, { route: "/investments", auth: true })

    expect(await screen.findByText("Aucune action hors ETF à comparer.")).toBeInTheDocument()
    expect(screen.queryByText("Écart (actions − référence)")).not.toBeInTheDocument()
  })

  it("sans action hors ETF ni référence : la carte explique au lieu de disparaître", async () => {
    server.use(http.get(apiUrl("/analytics/stock-picking-benchmark"), () => HttpResponse.json(body({
      lines: [], candidates: [], benchmark_ticker: null, benchmark_name: null, start_date: null,
      warnings: ["Aucun ETF détenu ni référence choisie : impossible de comparer le stock picking."],
    }))))
    renderWithProviders(<StockPickingBenchmark />, { route: "/investments", auth: true })

    expect(await screen.findByText("Aucune action hors ETF à comparer.")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Stock picking face à un indice" })).toBeInTheDocument()
    expect(screen.getByText(/impossible de comparer/)).toBeInTheDocument()
  })

  it("chargement en échec : message d'erreur au lieu d'un vide", async () => {
    server.use(http.get(apiUrl("/analytics/stock-picking-benchmark"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))
    renderWithProviders(<StockPickingBenchmark />, { route: "/investments", auth: true })

    expect(await screen.findByRole("alert")).toBeInTheDocument()
  })
})
