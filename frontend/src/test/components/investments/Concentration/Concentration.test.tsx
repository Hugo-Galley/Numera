/** Carte « Concentration » : écart au marché, blocs corrélés, stock picking redondant et référence de marché. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { safeStorage } from "@/lib/storage"
import { renderWithProviders } from "@/test/support/render"
import { apiUrl } from "@/test/support/handlers"
import { server } from "@/test/support/server"
import { Concentration } from "@/components/investments/Concentration"
import type { DiversityScannerResponse, MarketComparison } from "@/types/diversity"

const dimension = (rows: MarketComparison["sectors"]["rows"], active = 24) => ({ active_share_pct: active, covered_pct: 90, rows })

const market: MarketComparison = {
  name: "iShares MSCI ACWI",
  ticker: "SSAC.L",
  sectors: dimension([
    { name: "Technologie", portfolio_pct: 38, market_pct: 25, market_pct_is_upper_bound: false, gap_pts: 13 },
    { name: "Énergie", portfolio_pct: 2, market_pct: 4.5, market_pct_is_upper_bound: false, gap_pts: -2.5 },
  ]),
  countries: dimension([{ name: "USA", portfolio_pct: 70, market_pct: 64, market_pct_is_upper_bound: false, gap_pts: 6 }], 12),
  companies: dimension([{ name: "ASML", portfolio_pct: 6, market_pct: 0.4, market_pct_is_upper_bound: true, gap_pts: 5.6 }], 40),
}

const data = (overrides: Partial<DiversityScannerResponse> = {}) => ({
  score: 74.7,
  score_label: "Bon",
  alerts: [],
  etf_compositions: [{ profile_id: 1, profile_name: "Amundi MSCI World", tickers: ["CW8.PA"], value_eur: 9000, sources: {} }],
  concentration: {
    effective_bets: 3.2,
    exposures_count: 11,
    blocks: [{ members: ["Bitcoin USD", "Ethereum USD"], weight_pct: 7, mean_rho: 0.86 }],
    pairs_by_source: { prices: 40, composition: 12, unknown: 3 },
  },
  market,
  stock_picking: [
    { name: "Apple", ticker: "AAPL", indirect_value_eur: 295.4, correlation_with_core: 0.91, source: "prices", redundant: true },
    { name: "TotalEnergies", ticker: "TTE.PA", indirect_value_eur: 0, correlation_with_core: null, source: "unknown", redundant: false },
  ],
  coverage: { composition_pct: 82, with_prices_pct: 91 },
  ...overrides,
}) as unknown as DiversityScannerResponse

const isMasked = (element: Element) => element.closest(".privacy-masked, .amount-blur") !== null

describe("Concentration", () => {
  it("compare le portefeuille au marché, avec l'écart en points", () => {
    renderWithProviders(<Concentration data={data()} onReferenceChange={vi.fn()} />)

    const row = screen.getByRole("row", { name: /Technologie/ })
    expect(within(row).getAllByRole("cell").map((c) => c.textContent)).toEqual(["Technologie", expect.stringMatching(/^38\s%$/), expect.stringMatching(/^25\s%$/), "+13 pts"])
    expect(screen.getByText(/paris indépendants sur 11 lignes/).textContent).toBe("3,2 paris indépendants sur 11 lignes")
    expect(screen.getByText(/référence : iShares MSCI ACWI/)).toBeInTheDocument()
  })

  it("préfixe « ≤ » le poids du marché quand ce n'est qu'un majorant", async () => {
    const { user } = renderWithProviders(<Concentration data={data()} onReferenceChange={vi.fn()} />)

    await user.click(screen.getByRole("button", { name: "Sociétés" }))

    const row = screen.getByRole("row", { name: /ASML/ })
    expect(within(row).getAllByRole("cell")[2].textContent).toMatch(/^≤ 0,4\s%$/)
  })

  it("liste les blocs corrélés et le stock picking redondant", () => {
    renderWithProviders(<Concentration data={data()} onReferenceChange={vi.fn()} />)

    expect(screen.getByText("Bitcoin USD + Ethereum USD · ρ 0,86")).toBeInTheDocument()
    const apple = screen.getByText("Apple").closest("li") as HTMLElement
    expect(within(apple).getByText("Redondant")).toBeInTheDocument()
    expect(apple.textContent).toMatch(/Déjà 295,40\s€ via tes fonds · ρ 0,91 avec tes fonds \(par les cours\)/)
    const total = screen.getByText("TotalEnergies").closest("li") as HTMLElement
    expect(within(total).queryByText("Redondant")).not.toBeInTheDocument()
    expect(total.textContent).toContain("Absente de tes fonds · Corrélation inconnue")
  })

  it("en mode confidentialité, aucun montant en euros n'est lisible", async () => {
    safeStorage.setItem("privacy-mode", "true")
    renderWithProviders(<Concentration data={data()} onReferenceChange={vi.fn()} />)

    const card = screen.getByTestId("concentration")
    await waitFor(() => {
      const amounts = within(card).getAllByText(/€/)
      expect(amounts.length).toBeGreaterThan(0)
      for (const element of amounts) expect(isMasked(element)).toBe(true)
    })
  })

  it("sans référence de marché, le dit et n'affiche pas de tableau", () => {
    renderWithProviders(<Concentration data={data({ market: null })} onReferenceChange={vi.fn()} />)

    expect(screen.getByText(/Référence de marché indisponible/)).toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
    expect(screen.getByText("Bitcoin USD + Ethereum USD · ρ 0,86")).toBeInTheDocument()
  })

  it("une dimension sans part comparable affiche « — », pas un faux 0 %", () => {
    const unknown = { active_share_pct: 0, covered_pct: 0, rows: [] }
    renderWithProviders(
      <Concentration data={data({ market: { ...market, sectors: unknown, countries: unknown, companies: unknown } })} onReferenceChange={vi.fn()} />,
    )

    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3)
    expect(screen.queryByText(/^0\s%$/)).not.toBeInTheDocument()
  })

  it("ne s'affiche pas pour une réponse sans le modèle de concentration", () => {
    renderWithProviders(<Concentration data={data({ concentration: undefined, market: undefined })} onReferenceChange={vi.fn()} />)

    expect(screen.queryByTestId("concentration")).not.toBeInTheDocument()
  })
})

describe("Concentration : référence de marché", () => {
  it("choisir un profil envoie PUT {ticker} puis recharge", async () => {
    const bodies: unknown[] = []
    server.use(
      http.put(apiUrl("/analytics/diversity-scanner/market-reference"), async ({ request }) => {
        bodies.push(await request.json())
        return HttpResponse.json({ ticker: "CW8.PA" })
      }),
    )
    const onReferenceChange = vi.fn()
    const { user } = renderWithProviders(<Concentration data={data()} onReferenceChange={onReferenceChange} />)

    await user.click(screen.getByRole("combobox", { name: "Référence de marché" }))
    await user.click(await screen.findByRole("option", { name: "Amundi MSCI World (CW8.PA)" }))

    await waitFor(() => expect(onReferenceChange).toHaveBeenCalledTimes(1))
    expect(bodies).toEqual([{ ticker: "CW8.PA" }])
    expect(await screen.findByText("Référence de marché enregistrée")).toBeInTheDocument()
  })

  it("revenir au défaut envoie un ticker vide", async () => {
    const bodies: unknown[] = []
    server.use(
      http.put(apiUrl("/analytics/diversity-scanner/market-reference"), async ({ request }) => {
        bodies.push(await request.json())
        return HttpResponse.json({ ticker: null })
      }),
    )
    const { user } = renderWithProviders(<Concentration data={data()} onReferenceChange={vi.fn()} />)

    await user.click(screen.getByRole("combobox", { name: "Référence de marché" }))
    await user.click(await screen.findByRole("option", { name: "Par défaut (MSCI ACWI)" }))

    await waitFor(() => expect(bodies).toEqual([{ ticker: null }]))
  })

  it("un échec d'enregistrement prévient sans recharger", async () => {
    server.use(http.put(apiUrl("/analytics/diversity-scanner/market-reference"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))
    const onReferenceChange = vi.fn()
    const { user } = renderWithProviders(<Concentration data={data()} onReferenceChange={onReferenceChange} />)

    await user.type(screen.getByRole("textbox", { name: "Autre ticker" }), "IWDA.AS")
    await user.click(screen.getByRole("button", { name: "Appliquer" }))

    expect(await screen.findByText("Impossible d'enregistrer la référence de marché")).toBeInTheDocument()
    expect(onReferenceChange).not.toHaveBeenCalled()
  })
})
