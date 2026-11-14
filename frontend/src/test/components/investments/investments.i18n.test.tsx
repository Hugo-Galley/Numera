/** Dividendes d'un compte titres : textes, pluriels, phrase avec balises et montants en français comme en anglais. */
import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { setLanguage } from "@/i18n"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { DividendsCard } from "@/components/investments/DividendsCard"

const summary = (unlinkedCount: number) => ({
  totals: { count: 3, net_eur: 120, withholding_eur: 20, gross_eur: 140, last_12m_eur: 120 },
  by_month: [{ month: "2026-05", net_eur: 120 }],
  by_year: [{ year: 2026, count: 3, net_eur: 120, withholding_eur: 20, gross_eur: 140 }],
  by_ticker: [{ ticker: "TTE", asset_name: "TotalEnergies", count: 3, total_eur: 120, last_12m_eur: 120, last_date: "2026-05-20", yield_on_cost_pct: 4.5, current_yield_pct: 4.1 }],
  unlinked: { count: unlinkedCount, total_eur: 30 },
})

function serve(unlinkedCount: number) {
  server.use(http.get(apiUrl("/analytics/dividends"), () => HttpResponse.json(summary(unlinkedCount))))
}

describe("DividendsCard", () => {
  afterEach(() => setLanguage("fr"))

  it("en français : phrase au pluriel avec montant", async () => {
    serve(2)
    renderWithProviders(<DividendsCard accountId={3} />, { auth: true })
    expect(await screen.findByText("2 dividendes")).toBeInTheDocument()
    expect(screen.getByText(/ne sont rattachés à aucun titre/)).toBeInTheDocument()
    expect(screen.getAllByText("Dividendes").length).toBeGreaterThan(0)
  })

  it("en anglais : titres, accord au singulier, formats", async () => {
    await setLanguage("en")
    serve(1)
    renderWithProviders(<DividendsCard accountId={3} />, { auth: true })
    expect(await screen.findByText("1 dividend")).toBeInTheDocument()
    expect(screen.getByText(/isn't linked to any security/)).toBeInTheDocument()
    expect(screen.getAllByText("Dividends").length).toBeGreaterThan(0)
    expect(screen.getByRole("button", { name: /Link automatically/ })).toBeInTheDocument()
    expect(screen.getAllByText(/€120\.00 net/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/\(€140\.00 gross\)/).length).toBeGreaterThan(0)
    const row = screen.getAllByText("TotalEnergies")[0].closest("li, tr") as HTMLElement
    expect(within(row).getByText(/last: 20\/05\/2026/)).toBeInTheDocument()
  })
})
