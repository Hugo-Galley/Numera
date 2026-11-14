/** Provisions, prestations et créances en anglais : textes, pluriels, phrases à variables et formats. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { setLanguage } from "@/i18n"
import { MONTHS } from "@/pages/RecurringTransactions/types"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { intervalLabel } from "@/components/savings/ProvisionCard"
import type { Provision } from "@/components/savings/ProvisionCard"
import { ProvisionsSection } from "@/components/savings/ProvisionsSection"

const provision: Provision = {
  id: 3, name: "Taxe foncière", amount: 1200, interval_months: 12, due_date: "2026-10-15", category_id: null, account_id: null, note: null,
  active: true, category_name: null, account_name: null, next_due: "2026-10-15", previous_due: "2025-10-15", months_left: 4, monthly_amount: 100,
  target_now: 800, monthly_needed: 150, funded: null, status: "untracked", last_payment: null,
}

function serve() {
  server.use(
    http.get(apiUrl("/provisions"), () => HttpResponse.json([provision])),
    http.get(apiUrl("/provisions/summary"), () => HttpResponse.json({ monthly_total: 150, target_now_total: 800, behind_count: 0, accounts: [] })),
    http.get(apiUrl("/categories"), () => HttpResponse.json([])),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
  )
}

describe("épargne en anglais", () => {
  afterEach(() => setLanguage("fr"))

  it("provisions : titre, résumé mensuel, échéance et durée", async () => {
    await setLanguage("en")
    serve()
    renderWithProviders(<ProvisionsSection />, { auth: true })
    expect(await screen.findByText("Provisions")).toBeInTheDocument()
    expect(await screen.findByText(/€150\.00 \/ month to set aside/)).toBeInTheDocument()
    expect(await screen.findByText(/due on 15 Oct 2026/)).toBeInTheDocument()
    expect(await screen.findByText(/for 4 months/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /New provision/ })).toBeInTheDocument()
  })

  it("en français, mêmes écrans", async () => {
    serve()
    renderWithProviders(<ProvisionsSection />, { auth: true })
    expect(await screen.findByText("Provisions")).toBeInTheDocument()
    expect(await screen.findByText(/pendant 4 mois/)).toBeInTheDocument()
  })

  it("intervalles et mois abrégés suivent la langue, sans être figés à l'import", async () => {
    expect(intervalLabel(1)).toBe("Mensuelle")
    expect(intervalLabel(5)).toBe("Tous les 5 mois")
    expect(MONTHS[7].label).toBe("Août")
    await setLanguage("en")
    expect(intervalLabel(1)).toBe("Monthly")
    expect(intervalLabel(5)).toBe("Every 5 months")
    expect(MONTHS[7].label).toBe("Aug")
  })
})
