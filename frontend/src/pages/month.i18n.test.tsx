/** Mois (revue, hub) et Classement en anglais : titres, étapes, pluriels, noms de mois et onglets. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { setLanguage } from "@/i18n"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import type { MonthReview as MonthReviewData } from "@/types/monthReview"
import MonthHub from "./MonthHub"
import MonthReview from "./MonthReview"

const review: MonthReviewData = {
  year: 2026, month: 6, closed: false, closure: null, modified_since_close: false,
  categorize: { count: 3, total: 450, items: [{ id: 11, date: "2026-06-12T10:00:00", merchant: "Canapé", amount: 300, category_name: null, is_exceptional: false }] },
  accounts: { unverified_count: 0, accounts: [] },
  budget: {
    income: 3000, real_expenses: 2100, savings: 900, savings_rate: 30, burn_rate: 70, exceptional_expenses: 0, real_expenses_excl_exceptional: 2100,
    savings_excl_exceptional: 900, savings_rate_excl_exceptional: 30, burn_rate_excl_exceptional: 70, previous_real_expenses: 2000, alerts: [], top_expenses: [],
  },
}

function serve() {
  server.use(
    http.get(apiUrl("/analytics/budget-period"), () => HttpResponse.json({ current: { year: 2026, month: 7 } })),
    http.get(apiUrl("/categories"), () => HttpResponse.json([])),
    http.get(apiUrl("/month-review"), () => HttpResponse.json(review)),
  )
}

describe("Mois en anglais", () => {
  afterEach(() => setLanguage("fr"))

  it("revue : mois en toutes lettres, étapes et phrase avec pluriel", async () => {
    await setLanguage("en")
    serve()
    renderWithProviders(
      <Routes><Route path="/month/revue" element={<MonthReview />} /></Routes>,
      { route: "/month/revue?year=2026&month=6", auth: true },
    )
    expect(screen.getByText("June 2026")).toBeInTheDocument()
    expect(await screen.findByText(/3 uncategorized expenses, totaling/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /1\. Categorize/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /4\. Highlight/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Previous month" })).toBeInTheDocument()
  })

  it("revue en français : mêmes étapes", async () => {
    serve()
    renderWithProviders(
      <Routes><Route path="/month/revue" element={<MonthReview />} /></Routes>,
      { route: "/month/revue?year=2026&month=6", auth: true },
    )
    expect(await screen.findByText(/3 dépenses sans catégorie, soit/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /1\. Catégoriser/ })).toBeInTheDocument()
  })

  it("hub : onglets Bilan, Revue et Comparaison", async () => {
    await setLanguage("en")
    renderWithProviders(
      <Routes><Route path="/month" element={<MonthHub />} /></Routes>,
      { route: "/month", auth: true },
    )
    expect(screen.getByRole("link", { name: "Report" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Review" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Comparison" })).toBeInTheDocument()
  })
})
