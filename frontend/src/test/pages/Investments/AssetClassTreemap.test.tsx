/** Investissements : treemap des classes d'actifs et sa légende (couleurs, pourcentages, part non classée, détail). */
import { screen } from "@testing-library/react"
import { renderWithProviders } from "@/test/support/render"
import { AssetClassTreemap } from "@/pages/Investments/AssetClassTreemap"
import type { InvestmentsCtx } from "@/pages/Investments/useInvestments"
import { CATEGORY_COLORS, NEUTRAL_COLOR } from "@/lib/chartPalette"

const group = (name: string, value: number, percentage: number) => ({ name, value, percentage, items: [] })

const makeCtx = (byAssetClass = [group("Non classé", 9934, 99.34), group("Liquidités", 66, 0.66)]) => ({
  advancedAllocation: { by_asset_class: byAssetClass, by_sector: [group("Technologie", 10, 21.9)], by_zone: [] },
  diversity: null,
  getDrilldownItems: () => [],
  getDrilldownTitle: (p: string) => p,
  setDrillDown: vi.fn(),
}) as unknown as InvestmentsCtx

const dotOf = (label: string) => screen.getByText(label).previousElementSibling as HTMLElement

describe("Investissements : classes d'actifs", () => {
  it("écrit les pourcentages des classes d'actifs au format français", () => {
    renderWithProviders(<AssetClassTreemap ctx={makeCtx()} />)
    expect(screen.getByText(/^99,3\s%$/)).toBeInTheDocument()
    expect(screen.queryByText("99.34%")).not.toBeInTheDocument()
  })

  it("donne aux pastilles une couleur de la palette, grise seulement pour « Non classé »", () => {
    renderWithProviders(<AssetClassTreemap ctx={makeCtx()} />)
    expect(dotOf("Non classé").style.backgroundColor).toBe(rgb(NEUTRAL_COLOR))
    expect(dotOf("Liquidités").style.backgroundColor).toBe(rgb(CATEGORY_COLORS[1]))
  })

  it("ouvre le détail d'une classe depuis la légende", async () => {
    const ctx = makeCtx()
    const { user } = renderWithProviders(<AssetClassTreemap ctx={ctx} />)
    await user.click(screen.getByRole("button", { name: /Liquidités/ }))
    expect(ctx.setDrillDown).toHaveBeenCalledWith({ title: "Classe d'actif", items: [] })
  })

  it("explique comment classer une part non classée", () => {
    renderWithProviders(<AssetClassTreemap ctx={makeCtx()} />)
    expect(screen.getByText(/classe d'actifs/i, { selector: "p" })).toBeInTheDocument()
  })

  it("sans part non classée, pas d'explication", () => {
    renderWithProviders(<AssetClassTreemap ctx={makeCtx([group("Actions", 100, 100)])} />)
    expect(screen.queryByText(/classe d'actifs/i, { selector: "p" })).not.toBeInTheDocument()
  })
})

function rgb(hex: string) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  return `rgb(${r}, ${g}, ${b})`
}
