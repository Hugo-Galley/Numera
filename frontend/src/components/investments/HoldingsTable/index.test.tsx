/** Positions d'un compte titres : mode confidentialité (montants masqués) et option « titres et parts seulement ». */
import { screen, waitFor, within } from "@testing-library/react"
import { safeStorage } from "@/lib/storage"
import { renderWithProviders } from "@/test/render"
import type { PortfolioHolding } from "@/types/diversity"
import { HoldingsTable } from "."

const holding = (overrides: Partial<PortfolioHolding> = {}): PortfolioHolding => ({
  id: 1,
  account_id: 5,
  ticker: "CW8.PA",
  isin: "LU1681043599",
  asset_name: "Amundi MSCI World",
  quantity: 12.5,
  buy_price_avg: 480,
  currency: "EUR",
  current_price: 520.4,
  current_price_eur: 520.4,
  current_value_eur: 6505,
  total_invested_eur: 6000,
  gain_eur: 505,
  gain_pct: 8.42,
  is_etf: true,
  ...overrides,
})

const holdings = [holding(), holding({ id: 2, ticker: "AI.PA", isin: "FR0000120073", asset_name: "Air Liquide", quantity: 3, is_etf: false, current_value_eur: 540.3, total_invested_eur: 600, gain_eur: -59.7, gain_pct: -9.95 })]

function renderTable() {
  return renderWithProviders(<HoldingsTable accountId={5} accountName="PEA" holdings={holdings} onRefresh={vi.fn()} />, { auth: true })
}

/** Le tableau de bureau (la liste mobile est aussi rendue, masquée par CSS). */
const desktopTable = () => screen.getByRole("table")
const isMasked = (element: Element) => element.closest(".privacy-masked, .amount-blur") !== null

describe("HoldingsTable : confidentialité", () => {
  it("hors confidentialité, les montants sont affichés en clair", () => {
    renderTable()
    const value = within(desktopTable()).getByText(/6\s505,00\s€/)

    expect(document.body).not.toHaveClass("privacy-enabled")
    expect(value).toBeVisible()
    expect(value.closest(".privacy-masked")).toBeNull()
  })

  it("en mode confidentialité, chaque montant est masqué mais titres et parts restent lisibles", async () => {
    safeStorage.setItem("privacy-mode", "true")
    renderTable()
    const table = desktopTable()

    expect(document.body).toHaveClass("privacy-enabled")
    const amounts = [/6\s505,00\s€/, /6\s000,00\s€/, /\+505,00\s€/, /540,30\s€/, /-59,70\s€/, /520,40\s€/]
    await waitFor(() => {
      for (const amount of amounts) {
        for (const element of within(table).getAllByText(amount)) expect(isMasked(element)).toBe(true)
      }
    })
    expect(isMasked(within(table).getByText("CW8.PA"))).toBe(false)
    expect(isMasked(within(table).getByText("12.5"))).toBe(false)
  })

  it("l'option « titres et parts seulement » retire tous les montants", () => {
    safeStorage.setItem("hide-holding-values", "true")
    renderTable()
    const table = desktopTable()

    expect(screen.getByText("Titres détenus et nombre de parts.")).toBeInTheDocument()
    expect(within(table).queryByRole("columnheader", { name: "Valeur totale" })).not.toBeInTheDocument()
    expect(within(table).queryByText(/€/)).not.toBeInTheDocument()
    expect(within(table).getByText("Amundi MSCI World")).toBeInTheDocument()
    expect(within(table).getByText("12.5")).toBeInTheDocument()
  })
})
