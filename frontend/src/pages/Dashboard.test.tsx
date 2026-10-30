/** Tableau de bord : un bloc en échec affiche un ErrorState sans empêcher les onglets ; « Réessayer » recharge. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import Dashboard from "./Dashboard"

const { stub } = vi.hoisted(() => ({
  /** Onglet factice : son nom et les props reçues (null / vide = bloc non chargé). */
  stub: (name: string) => (props: Record<string, unknown>) => (
    <section aria-label={name}>
      {Object.entries(props)
        .filter(([key]) => !["drilldownScope", "displayCurrency", "onEventsChanged", "accounts"].includes(key))
        .map(([key, value]) => (
          <p key={key}>
            {key}: {value === null || (Array.isArray(value) && value.length === 0) ? "vide" : "chargé"}
          </p>
        ))}
    </section>
  ),
}))
vi.mock("@/components/dashboard/tabs/OverviewTab", () => ({ OverviewTab: stub("Aperçu") }))
vi.mock("@/components/dashboard/tabs/BudgetsTab", () => ({ BudgetsTab: stub("Budgets") }))
vi.mock("@/components/dashboard/tabs/MerchantsTab", () => ({ MerchantsTab: stub("Marchands") }))
vi.mock("@/components/dashboard/tabs/SubscriptionsTab", () => ({ SubscriptionsTab: stub("Abonnements") }))
vi.mock("@/components/dashboard/tabs/InsightsTab", () => ({ InsightsTab: stub("Analyse") }))
vi.mock("@/components/dashboard/tabs/HistoryTab", () => ({ HistoryTab: stub("Historique") }))
vi.mock("@/components/dashboard/tabs/ProjectionsTab", () => ({ ProjectionsTab: stub("Projections") }))
vi.mock("@/components/dashboard/DashboardKPIs", () => ({ DashboardKPIs: stub("KPI") }))
vi.mock("@/components/month-review/MonthReviewPopup", () => ({ MonthReviewPopup: () => null }))

/** Tous les blocs répondent `{ items: [1] }` sauf ceux de `failing` (500). Mois budgétaire : juin 2026. */
function serveDashboard(failing: string[]) {
  const calls: string[] = []
  server.use(
    http.get(apiUrl("/accounts"), () => HttpResponse.json([{ id: 1, name: "Compte joint", type: "courant", currency: "EUR", active: true }])),
    http.get(apiUrl("/analytics/budget-period"), () =>
      HttpResponse.json({ current: { year: 2026, month: 6 }, start: "2026-05-28", end: "2026-06-27" }),
    ),
    http.get(apiUrl("/analytics/*"), ({ request }) => {
      const path = new URL(request.url).pathname.replace(/^.*\/analytics/, "/analytics")
      calls.push(path)
      return failing.includes(path) ? HttpResponse.json({ detail: "boom" }, { status: 500 }) : HttpResponse.json({ items: [1] })
    }),
    http.get(apiUrl("/month-review/closures"), () => HttpResponse.json([])),
    http.get(apiUrl("/financial-events"), () => HttpResponse.json([])),
  )
  return calls
}

describe("Dashboard : échec partiel", () => {
  it("un bloc en échec : ErrorState avec le nombre de blocs, les autres onglets affichent leurs données", async () => {
    serveDashboard(["/analytics/top-merchants"])
    renderWithProviders(<Dashboard />, { auth: true })

    expect(await screen.findByText("1 bloc(s) du tableau de bord n'ont pas pu être chargés.")).toBeInTheDocument()
    expect(screen.getByRole("region", { name: "Aperçu" })).toHaveTextContent("expensesByCategory: chargé")
    expect(screen.getByRole("region", { name: "Aperçu" })).toHaveTextContent("sankeyData: chargé")
    expect(screen.getByRole("region", { name: "KPI" })).toHaveTextContent("analytics: chargé")
    expect(screen.getByRole("tab", { name: "Dépenses" })).toBeEnabled()
  })

  it("« Réessayer » relance le chargement et retire l'erreur", async () => {
    const failing = ["/analytics/sankey"]
    const calls = serveDashboard(failing)
    const { user } = renderWithProviders(<Dashboard />, { auth: true })
    await screen.findByText("1 bloc(s) du tableau de bord n'ont pas pu être chargés.")
    const sankeyCalls = calls.filter((c) => c === "/analytics/sankey").length

    failing.length = 0
    await user.click(screen.getByRole("button", { name: "Réessayer" }))

    await waitFor(() => expect(screen.getByRole("region", { name: "Aperçu" })).toHaveTextContent("sankeyData: chargé"))
    expect(screen.queryByText(/bloc\(s\) du tableau de bord/)).not.toBeInTheDocument()
    expect(calls.filter((c) => c === "/analytics/sankey").length).toBe(sankeyCalls + 1)
  })

  it("aucun échec : pas d'ErrorState", async () => {
    serveDashboard([])
    renderWithProviders(<Dashboard />, { auth: true })

    await waitFor(() => expect(screen.getByRole("region", { name: "Aperçu" })).toHaveTextContent("sankeyData: chargé"))
    expect(screen.queryByRole("button", { name: "Réessayer" })).not.toBeInTheDocument()
  })
})
