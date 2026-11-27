/** Donut de répartition : entreprises (ETF décomposés), vues, provenance en direct / via ETF, zoom et doublons. */
import { screen } from "@testing-library/react"
import { PortfolioBreakdown, type BreakdownData } from "@/components/investments/PortfolioBreakdown"
import { renderWithProviders } from "@/test/support/render"

const company = (name: string, ticker: string, direct: number, indirect: number, overlap = false) => ({
  name, ticker, direct_value_eur: direct, indirect_value_eur: indirect, total_value_eur: direct + indirect, has_overlap: overlap,
})
const holding = (ticker: string, name: string, value: number, etf = false) => ({ ticker, name, value_eur: value, etf_profile_id: etf ? 1 : null })

// 1 000 € : MSCI World 500 € (décomposé) + Apple 300 € et Total 200 € en direct
const data = (extra: Partial<BreakdownData> = {}): BreakdownData => ({
  totals: { stocks_eur: 1000, direct_eur: 500, etf_eur: 500, holdings_count: 3, etfs_count: 1 },
  top_underlying_companies: [
    company("Apple Inc.", "AAPL", 300, 25, true),
    company("TotalEnergies SE", "TTE", 200, 0),
    company("Microsoft", "MSFT", 0, 20),
  ],
  holdings: [holding("AAPL", "Apple", 300), holding("TTE", "Total", 200), holding("CW8", "MSCI World", 500, true)],
  sectors: [{ name: "Technologie", value_eur: 500 }],
  countries: [{ name: "USA", value_eur: 600 }],
  ...extra,
})

describe("PortfolioBreakdown", () => {
  it("liste les entreprises, regroupe le reste en « Autres » et signale les doublons", () => {
    renderWithProviders(<PortfolioBreakdown data={data()} scope="portfolio" />)

    expect(screen.getByText("Répartition du portefeuille")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
    expect(screen.getByText("Doublon")).toBeInTheDocument()
    // 1 000 − 545 de sociétés nommées
    expect(screen.getByText("Autres entreprises")).toBeInTheDocument()
    expect(screen.getByText(/455,00/)).toBeInTheDocument()
    expect(screen.getByText("Valeur des positions")).toBeInTheDocument()
  })

  it("filtre par provenance : en direct, puis via ETF", async () => {
    const { user } = renderWithProviders(<PortfolioBreakdown data={data()} scope="portfolio" />)

    await user.click(screen.getByRole("button", { name: "En direct" }))
    expect(screen.getByText("Détenu en direct")).toBeInTheDocument()
    expect(screen.getByText("TotalEnergies SE")).toBeInTheDocument()
    expect(screen.queryByText("Microsoft")).not.toBeInTheDocument()
    expect(screen.queryByText("Doublon")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Via ETF" }))
    expect(screen.getByText("Détenu via ETF")).toBeInTheDocument()
    expect(screen.getByText("Microsoft")).toBeInTheDocument()
    expect(screen.queryByText("TotalEnergies SE")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Positions" }))
    expect(screen.getByText("MSCI World")).toBeInTheDocument()
    expect(screen.queryByText("Total")).not.toBeInTheDocument()
  })

  it("pays par leur nom, sans choix de provenance ; zoom qui masque « Autres »", async () => {
    const { user } = renderWithProviders(<PortfolioBreakdown data={data()} scope="account" />)

    await user.click(screen.getByRole("button", { name: "Pays" }))
    expect(screen.getByText("États-Unis")).toBeInTheDocument()
    expect(screen.queryByRole("group", { name: "Provenance" })).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Entreprises" }))
    await user.click(screen.getByRole("checkbox", { name: /Zoomer sur les lignes nommées/ }))
    expect(screen.queryByText("Autres entreprises")).not.toBeInTheDocument()
    expect(screen.getByText("Lignes nommées")).toBeInTheDocument()
    expect(screen.getByText(/54,5.*du compte/)).toBeInTheDocument()
  })

  it("compte crypto sans ETF : secteur « Crypto-actifs », ni pays, ni provenance, ni zoom", async () => {
    const { user } = renderWithProviders(<PortfolioBreakdown scope="account" data={data({
      sectors: [{ name: "Crypto-actifs", value_eur: 500 }],
      countries: [],
      totals: { stocks_eur: 500, direct_eur: 500, etf_eur: 0, holdings_count: 2, etfs_count: 0 },
      top_underlying_companies: [company("Ethereum USD", "ETH-USD", 300, 0), company("Bitcoin USD", "BTC-USD", 200, 0)],
      holdings: [holding("ETH-USD", "Ethereum", 300), holding("BTC-USD", "Bitcoin", 200)],
    })} />)

    expect(screen.getByText("Ethereum USD")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Pays" })).not.toBeInTheDocument()
    expect(screen.queryByRole("group", { name: "Provenance" })).not.toBeInTheDocument()
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Secteurs" }))
    expect(screen.getByText("Crypto-actifs")).toBeInTheDocument()
  })

  it("sans position valorisée : rien n'est affiché", () => {
    renderWithProviders(<PortfolioBreakdown scope="portfolio" data={data({ totals: { stocks_eur: 0, direct_eur: 0, etf_eur: 0, holdings_count: 0, etfs_count: 0 } })} />)
    expect(screen.queryByText("Répartition du portefeuille")).not.toBeInTheDocument()
  })
})
