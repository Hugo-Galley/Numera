/** Investissements : cartes de chiffres, la valeur ne doit jamais être coupée (1024 px avec la barre latérale). */
import { screen } from "@testing-library/react"
import { renderWithProviders } from "@/test/support/render"
import { InvestmentsKpis } from "@/pages/Investments/InvestmentsKpis"
import type { InvestmentsCtx } from "@/pages/Investments/useInvestments"

const ctx = {
  allocation: { items: [{}, {}], total_current_value: 24015.12, total_gain_eur: 2015.12, total_performance_pct: 9.16 },
  diversity: { score: 61.2, score_label: "Correct", alerts: [] },
} as unknown as InvestmentsCtx

describe("Investissements : cartes de chiffres", () => {
  it("reste sur 2 colonnes jusqu'aux grands écrans (4 seulement à partir de xl)", () => {
    renderWithProviders(<InvestmentsKpis ctx={ctx} />)
    const grid = screen.getByText(/valeur totale/i).closest(".grid") as HTMLElement
    expect(grid.className).toContain("xl:grid-cols-4")
    expect(grid.className).not.toMatch(/(^|\s)md:grid-cols-4/)
  })

  it("n'impose pas la grande taille de police aux écrans moyens", () => {
    renderWithProviders(<InvestmentsKpis ctx={ctx} />)
    const value = screen.getByText(/24\s015,12/).closest("div") as HTMLElement
    expect(value.className).not.toMatch(/(^|\s)text-3xl/)
    expect(value.className).not.toContain("truncate")
  })

  it("affiche le score et son libellé, sans répéter la carte Concentration", () => {
    const withModel = {
      ...ctx,
      diversity: { score: 74.7, score_label: "Bon", alerts: [], concentration: { effective_bets: 3.2, exposures_count: 11, blocks: [] }, market: { name: "iShares MSCI ACWI" } },
    } as unknown as InvestmentsCtx
    renderWithProviders(<InvestmentsKpis ctx={withModel} />)

    expect(screen.getByText("74,7")).toBeInTheDocument()
    expect(screen.getByText("Bon")).toBeInTheDocument()
    expect(screen.queryByText(/paris indépendants/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Écart au marché/)).not.toBeInTheDocument()
  })
})
