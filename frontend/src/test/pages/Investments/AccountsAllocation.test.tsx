/** Investissements : légende de la répartition par compte, pastilles visibles dans les deux thèmes. */
import { screen } from "@testing-library/react"
import { renderWithProviders } from "@/test/support/render"
import { AccountsAllocation } from "@/pages/Investments/AccountsAllocation"
import type { InvestmentsCtx } from "@/pages/Investments/useInvestments"
import { CATEGORY_COLORS } from "@/lib/chartPalette"

const items = [
  { account_id: 1, account_name: "PEA", current_value: 15000, percentage: 62.5, gain_eur: 1000, performance_pct: 7, currency: "EUR" },
  { account_id: 2, account_name: "CTO", current_value: 9000, percentage: 37.5, gain_eur: -200, performance_pct: -2, currency: "EUR" },
]
const ctx = {
  allocation: { items, total_current_value: 24000 },
  chartData: items.map((i) => ({ name: i.account_name, value: i.current_value, percentage: i.percentage, id: i.account_id })),
  handleAccountClick: vi.fn(),
} as unknown as InvestmentsCtx

describe("Investissements : répartition par compte", () => {
  it("colore chaque compte avec une teinte distincte de la palette", () => {
    renderWithProviders(<AccountsAllocation ctx={ctx} />)
    const dot = (name: string) => (screen.getByText(name).previousElementSibling as HTMLElement).style.backgroundColor
    expect(dot("PEA")).toBe(rgb(CATEGORY_COLORS[0]))
    expect(dot("CTO")).toBe(rgb(CATEGORY_COLORS[1]))
  })
})

function rgb(hex: string) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  return `rgb(${r}, ${g}, ${b})`
}
