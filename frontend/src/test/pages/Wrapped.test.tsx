/** Bilan annuel : année choisie dans l'adresse, chiffres clés comparés à l'année précédente, listes, abonnements, story plein écran, erreurs. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { LocationDisplay } from "@/test/support/LocationDisplay"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import Wrapped from "@/pages/Wrapped"
import type { WrappedReport, WrappedTotals } from "@/types/wrapped"

const totals = (overrides: Partial<WrappedTotals> = {}): WrappedTotals => ({
  income: 36000, real_expenses: 24000, saved: 12000, savings_rate: 33, invested: 6000, dividends: 150,
  net_worth_start: 20000, net_worth_end: 38000, net_worth_change: 18000, subscriptions_cost: 480, expense_count: 1234, ...overrides,
})
const report = (overrides: Partial<WrappedReport> = {}): WrappedReport => ({
  year: 2025, available_years: [2024, 2025], has_data: true, is_partial: false, months_covered: 12, totals: totals(),
  months: [{ month: 1, income: 3000, real_expenses: 2000, saved: 1000 }, { month: 2, income: 3000, real_expenses: 1500, saved: 1500 }],
  most_expensive_month: { month: 1, income: 3000, real_expenses: 2000, saved: 1000 },
  thriftiest_month: { month: 2, income: 3000, real_expenses: 1500, saved: 1500 },
  top_categories: [{ name: "Courses", icon: null, color: "#10b981", total: 4800, percentage: 20, work_hours: 120 }],
  top_merchants: [{ merchant: "Carrefour", total: 3000, work_hours: null }, { merchant: "SNCF", total: 900, work_hours: null }],
  biggest_expense: { merchant: "Garage Martin", amount: 1500, date: "2025-03-04T00:00:00", category: "Auto", work_hours: 40 },
  hourly_rate: 20, real_expenses_work_hours: 1200, net_worth_change_pct: 90,
  new_subscriptions: [{ name: "Netflix", monthly_cost: 13 }], stopped_subscriptions: [{ name: "Vieux service", monthly_cost: 10 }], stopped_subscriptions_yearly_saving: 120,
  previous: { year: 2024, totals: totals({ income: 34000 }), income_change_pct: 5.9, real_expenses_change_pct: -3, savings_rate_change_pts: 2, net_worth_change_diff: 4000, invested_change_pct: 10 },
  ...overrides,
})

function serve(reports: Record<string, WrappedReport | number> = { "2025": report() }) {
  const years: string[] = []
  server.use(
    http.get(apiUrl("/analytics/wrapped"), ({ request }) => {
      const year = new URL(request.url).searchParams.get("year") ?? ""
      years.push(year)
      const found = reports[year]
      if (typeof found === "number") return HttpResponse.json({ detail: "KO" }, { status: found })
      return found ? HttpResponse.json(found) : HttpResponse.json(report({ year: Number(year), has_data: false }))
    }),
    http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ configured: true, hourly_rate: 20, work_hours_per_day: 7 })),
  )
  return years
}

const lastOf = <T,>(items: T[]) => items[items.length - 1]

const view = (route = "/wrapped?year=2025") =>
  renderWithProviders(<WorkTimeProvider><Wrapped /><LocationDisplay /></WorkTimeProvider>, { route, auth: true })

describe("Bilan annuel", () => {
  it("charge l'année de l'adresse et affiche les chiffres clés comparés à l'année précédente", async () => {
    const years = serve()
    view()

    expect(await screen.findByText("Année complète")).toBeInTheDocument()
    expect(years).toEqual(["2025"])
    expect(screen.getByText(/36\s000,00/)).toBeInTheDocument()
    expect(screen.getByText("Revenus")).toBeInTheDocument()
    expect(screen.getByText("Taux d'épargne")).toBeInTheDocument()
    expect(screen.getByText(/90\s?% sur l'année/)).toBeInTheDocument()
    expect(screen.getAllByText(/2024/).length).toBeGreaterThan(0)
  })

  it("accroche : nombre de dépenses et marchand en tête", async () => {
    serve()
    view()

    expect(await screen.findByText(/1\s234 dépenses, Carrefour en tête/)).toBeInTheDocument()
  })

  it("plus gros postes, top marchands, plus grosse dépense et mois extrêmes", async () => {
    serve()
    view()
    await screen.findByText("Année complète")

    expect(screen.getAllByText("Courses").length).toBeGreaterThan(0)
    expect(screen.getByText("Carrefour")).toBeInTheDocument()
    expect(screen.getByText("SNCF")).toBeInTheDocument()
    expect(screen.getByText(/Garage Martin/)).toBeInTheDocument()
    expect(screen.getByText("Mois le plus cher :")).toBeInTheDocument()
    expect(screen.getByText("Mois le plus sobre :")).toBeInTheDocument()
  })

  it("abonnements : nouveaux, arrêtés et économie annuelle", async () => {
    serve()
    view()
    await screen.findByText("Année complète")

    expect(screen.getByText("Netflix")).toBeInTheDocument()
    expect(screen.getByText("Vieux service")).toBeInTheDocument()
    expect(screen.getByText(/120,00\s€ \/ an économisés/)).toBeInTheDocument()
  })

  it("sans abonnement nouveau ni arrêté : « Aucun » deux fois", async () => {
    serve({ "2025": report({ new_subscriptions: [], stopped_subscriptions: [], top_merchants: [], biggest_expense: null, previous: null, net_worth_change_pct: null }) })
    view()
    await screen.findByText("Année complète")

    expect(screen.getAllByText("Aucun")).toHaveLength(2)
    expect(screen.getByText(/aucun marchand/)).toBeInTheDocument()
  })

  it("année en cours : période « Janvier → mois » et valeur « Aujourd'hui »", async () => {
    serve({ "2025": report({ is_partial: true, months_covered: 6 }) })
    view()

    expect(await screen.findByText(/Janvier → juin/i)).toBeInTheDocument()
    expect(screen.getByText("Aujourd'hui")).toBeInTheDocument()
  })

  it("année sans donnée : message qui invite à importer", async () => {
    serve({ "2025": report({ has_data: false }) })
    view()

    expect(await screen.findByText("Aucune donnée pour 2025")).toBeInTheDocument()
    expect(screen.getByText(/Importe ou saisis des transactions/)).toBeInTheDocument()
  })

  it("changer d'année dans le sélecteur recharge le bilan et met l'adresse à jour", async () => {
    const years = serve({ "2025": report(), "2024": report({ year: 2024, previous: null }) })
    const { user } = view()
    await screen.findByText("Année complète")

    await user.click(screen.getByRole("combobox"))
    await user.click(await screen.findByRole("option", { name: "2024" }))

    await waitFor(() => expect(years).toContain("2024"))
    expect(await screen.findByLabelText("adresse")).toHaveTextContent("/wrapped?year=2024")
  })

  it("bilan en échec : message avec « Réessayer » qui relance le chargement", async () => {
    let calls = 0
    server.use(
      http.get(apiUrl("/analytics/wrapped"), () => { calls += 1; return calls === 1 ? HttpResponse.json({ detail: "KO" }, { status: 500 }) : HttpResponse.json(report()) }),
      http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ configured: false, hourly_rate: null, work_hours_per_day: 7 })),
    )
    const { user } = view()

    expect(await screen.findByText("Le bilan annuel n'a pas pu être chargé.")).toBeInTheDocument()
    expect(await screen.findByText("Impossible de charger le bilan annuel")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /Réessayer/ }))

    expect(await screen.findByText("Année complète")).toBeInTheDocument()
    expect(calls).toBe(2)
  })

  it("« Revivre mon année » ouvre la story, qu'on referme avec « Fermer »", async () => {
    serve()
    const { user } = view()
    await screen.findByText("Année complète")

    await user.click(screen.getByRole("button", { name: "Revivre mon année" }))
    const close = await screen.findByRole("button", { name: "Fermer" })
    expect(screen.getByRole("button", { name: "Carte 1" })).toBeInTheDocument()
    await user.click(close)

    await waitFor(() => expect(screen.queryByRole("button", { name: "Carte 1" })).not.toBeInTheDocument())
  })

  it("la story avance carte par carte et se termine à la dernière", async () => {
    serve()
    const { user } = view()
    await screen.findByText("Année complète")
    await user.click(screen.getByRole("button", { name: "Revivre mon année" }))
    await screen.findByRole("button", { name: "Carte 1" })

    const total = screen.getAllByRole("button", { name: /^Carte \d+$/ }).length
    for (let i = 1; i < total; i++) await user.click(lastOf(screen.getAllByRole("button", { name: "Suivant" })))
    await user.click(screen.getByRole("button", { name: "Terminer" }))

    await waitFor(() => expect(screen.queryByRole("button", { name: "Carte 1" })).not.toBeInTheDocument())
  })
})
