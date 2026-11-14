/** Bilan du mois : chargement sur le mois budgétaire courant, navigation entre mois, clôture, budgets, anomalies, erreurs. */
import { screen, waitFor } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { LocationDisplay } from "@/test/support/LocationDisplay"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import MonthlyReport from "@/pages/MonthlyReport"
import type { BudgetLine, MonthlyReportData } from "@/components/monthly-report/types"

const flow = (amount: number) => ({ amount, percentage: 10, diff_prev_month: 0, diff_prev_month_pct: 0 })
const report = (overrides: Partial<MonthlyReportData> = {}): MonthlyReportData => ({
  month: 6, year: 2026, income: 3000, real_expenses: 1800, savings_rate: 20, net_worth_change: 450,
  top_categories: [{ id: 3, name: "Courses", total: 400, prev_total: 350 }],
  comparison: { income_diff: 100, income_diff_pct: 3, expenses_diff: -80, expenses_diff_pct: -4 },
  insights: [{ type: "anomaly", title: "Dépense inhabituelle", description: "Garage : 900 €", severity: "high" }, { type: "positive", title: "Bravo", description: "x", severity: "low" }],
  exceptional_expenses: 0, real_expenses_excl_exceptional: 1800, savings_rate_excl_exceptional: 20,
  money_flow: { income: 3000, fixed_charges: flow(900), variable_expenses: flow(900), savings: flow(300), investments: flow(200), remainder: flow(700) },
  ...overrides,
})
const budgetLine = (overrides: Partial<BudgetLine> = {}): BudgetLine => ({ category_id: 3, category_name: "Courses", monthly_limit: 500, monthly_spent: 400, monthly_ratio: 0.8, ...overrides })

/** Serveur du bilan : `reports` par « année-mois » ; les mois demandés sont consignés. */
function serve({ current = { year: 2026, month: 6 }, reports = { "2026-6": report(), "2026-5": report({ month: 5, income: 2800 }) } as Record<string, MonthlyReportData>, budgets = [budgetLine()], closures = [] as object[] } = {}) {
  const requested: string[] = []
  server.use(
    http.get(apiUrl("/analytics/budget-period"), () => HttpResponse.json({ ...current, mode: "civil", start: "2026-06-01", end: "2026-07-01", current })),
    http.get(apiUrl("/analytics/monthly-report"), ({ request }) => {
      const p = new URL(request.url).searchParams
      const key = `${p.get("year")}-${p.get("month")}`
      requested.push(key)
      return reports[key] ? HttpResponse.json(reports[key]) : HttpResponse.json({ detail: "Introuvable" }, { status: 404 })
    }),
    http.get(apiUrl("/analytics/budget-alerts"), () => HttpResponse.json(budgets)),
    http.get(apiUrl("/month-review/closures"), () => HttpResponse.json(closures)),
  )
  return requested
}

const view = () => renderWithProviders(<><MonthlyReport /><LocationDisplay /></>, { route: "/month/bilan", auth: true })

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date("2026-06-15T10:00:00"))
})
afterEach(() => vi.useRealTimers())

describe("Bilan du mois", () => {
  it("ouvre le mois budgétaire courant avec revenus, dépenses réelles et montant mis de côté", async () => {
    const requested = serve()
    view()

    expect(await screen.findByText("Juin 2026")).toBeInTheDocument()
    expect(await screen.findByText(/3\s000,00/)).toBeInTheDocument()
    expect(screen.getByText("Revenus")).toBeInTheDocument()
    expect(screen.getByText("Dépenses réelles")).toBeInTheDocument()
    expect(screen.getAllByText("Mis de côté").length).toBeGreaterThan(0)
    expect(requested).toEqual(["2026-6"])
  })

  it("le mois budgétaire du serveur prime sur le mois civil", async () => {
    const requested = serve({ current: { year: 2026, month: 5 } })
    view()

    expect(await screen.findByText("Mai 2026")).toBeInTheDocument()
    await waitFor(() => expect(requested).toEqual(["2026-5"]))
  })

  it("budgets tenus ou dépassés, et anomalies à regarder", async () => {
    serve({ budgets: [budgetLine(), budgetLine({ category_id: 4, category_name: "Loisirs", monthly_limit: 100, monthly_spent: 130, monthly_ratio: 1.3 })] })
    view()

    expect(await screen.findByText("Dépense inhabituelle")).toBeInTheDocument()
    expect(screen.getByText("Garage : 900 €")).toBeInTheDocument()
    expect(screen.queryByText("Bravo")).not.toBeInTheDocument()
    expect(screen.getByText("Loisirs")).toBeInTheDocument()
    expect(screen.getByText(/Dépassé de|dépassé/i)).toBeInTheDocument()
  })

  it("sans anomalie ni budget : « Rien d'anormal ce mois-ci »", async () => {
    serve({ reports: { "2026-6": report({ insights: [] }) }, budgets: [] })
    view()

    expect(await screen.findByText(/Rien d'anormal/)).toBeInTheDocument()
  })

  it("dépenses exceptionnelles : le total hors exceptionnel est annoncé", async () => {
    serve({ reports: { "2026-6": report({ exceptional_expenses: 600, real_expenses_excl_exceptional: 1200 }) } })
    view()

    expect((await screen.findAllByText(/hors exceptionnel/)).length).toBeGreaterThan(0)
  })

  it("mois précédent puis suivant ; « Mois suivant » est désactivé sur le dernier mois", async () => {
    const requested = serve()
    const { user } = view()
    await screen.findByText("Juin 2026")
    // l'en-tête s'affiche avant le bilan : cliquer pendant le chargement est ignoré par la page
    await waitFor(() => expect(requested).toEqual(["2026-6"]))
    expect(await screen.findByText(/3\s000,00/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Mois suivant" })).toBeDisabled()

    await user.click(screen.getByRole("button", { name: "Mois précédent" }))
    expect(await screen.findByText("Mai 2026")).toBeInTheDocument()
    await waitFor(() => expect(requested).toContain("2026-5"))
    await waitFor(() => expect(screen.getByRole("button", { name: "Mois suivant" })).toBeEnabled())

    await user.click(screen.getByRole("button", { name: "Mois suivant" }))
    expect(await screen.findByText("Juin 2026")).toBeInTheDocument()
  })

  it("mois non clôturé : lien vers la revue de fin de mois avec l'année et le mois", async () => {
    serve()
    const { user } = view()

    await user.click(await screen.findByRole("link", { name: /Revue de fin de mois à faire/ }))

    expect(await screen.findByLabelText("adresse")).toHaveTextContent("/month/revue?year=2026&month=6")
  })

  it("mois clôturé : le lien l'indique avec le nombre de points non résolus", async () => {
    serve({ closures: [{ year: 2026, month: 6, unresolved_count: 2 }, { year: 2026, month: 5, unresolved_count: 0 }] })
    view()

    expect(await screen.findByRole("link", { name: /Mois clôturé · 2 points non résolus/ })).toBeInTheDocument()
  })

  it("bilan introuvable : message et « Réessayer » relance le chargement", async () => {
    let calls = 0
    serve()
    server.use(http.get(apiUrl("/analytics/monthly-report"), () => {
      calls += 1
      return calls === 1 ? HttpResponse.json({ detail: "KO" }, { status: 500 }) : HttpResponse.json(report())
    }))
    const { user } = view()

    expect(await screen.findByText("Impossible de charger le bilan.")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Réessayer" }))

    expect(await screen.findByText("Revenus")).toBeInTheDocument()
    expect(calls).toBe(2)
  })

  it("budgets ou clôtures indisponibles : le bilan s'affiche quand même", async () => {
    serve()
    server.use(
      http.get(apiUrl("/analytics/budget-alerts"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
      http.get(apiUrl("/month-review/closures"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
    )
    view()

    expect(await screen.findByText("Revenus")).toBeInTheDocument()
  })
})
