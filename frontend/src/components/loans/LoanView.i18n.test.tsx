/** Vue d'un crédit en anglais : titres, phrases avec montants et durées, échéancier. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { setLanguage } from "@/i18n"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { LoanView } from "./LoanView"
import type { LoanSummary } from "./types"

const loan: LoanSummary = {
  id: 8, account_id: 12, name: "Prêt appartement", institution: "BRED", logo: null, color: null, kind: "immobilier",
  principal: 200000, annual_rate_pct: 3.6, duration_months: 300, start_date: "2024-02-05", insurance_monthly: 25.5,
  monthly_payment: 1012.5, remaining_principal: 190000, repaid_pct: 5, end_date: "2049-01-05", total_interest: 103750,
  total_insurance: 7650, total_cost: 111400, prepayments: [],
}

describe("LoanView en anglais", () => {
  afterEach(() => setLanguage("fr"))

  it("traduit les titres, la ligne de synthèse et l'échéancier", async () => {
    await setLanguage("en")
    server.use(
      http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
      http.get(apiUrl("/loans/by-account/12"), () => HttpResponse.json(loan)),
      http.get(apiUrl("/loans/8/schedule"), () => HttpResponse.json([
        { n: 1, date: "2024-02-05", payment: 1012.5, interest: 600, principal: 412.5, insurance: 25.5, remaining: 199587.5, prepayment: 0 },
      ])),
    )
    renderWithProviders(
      <Routes><Route path="/accounts/12" element={<LoanView accountId={12} />} /></Routes>,
      { route: "/accounts/12", auth: true },
    )
    expect(await screen.findByText("mortgage loan")).toBeInTheDocument()
    expect(screen.getByText(/· 3\.60% over 25 years/)).toBeInTheDocument()
    expect(screen.getByText("Simulate an early repayment")).toBeInTheDocument()
    expect(screen.getByText("1 payment. Tap a year for details.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Simulate" })).toBeInTheDocument()
  })
})
