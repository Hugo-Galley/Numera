/** Chargement du tableau de bord : un endpoint en échec n'empêche pas les autres, réponses obsolètes ignorées. */
import type { ReactNode } from "react"
import { act, renderHook, screen, waitFor } from "@testing-library/react"
import { delay, http, HttpResponse } from "msw"
import { Toaster } from "@/components/ui/sonner"
import { apiUrl } from "@/test/handlers"
import { server } from "@/test/server"
import { useDashboardData } from "./useDashboardData"

const wrapper = ({ children }: { children: ReactNode }) => (
  <>
    {children}
    <Toaster />
  </>
)

interface Options {
  /** Chemins (sans query) qui répondent 500. */
  failing?: string[]
  /** Retard de réponse selon le mois demandé. */
  delayFor?: (month: number | null) => number
}

/** Répond à chaque bloc ; `/analytics/budget` renvoie le mois et le compte reçus pour vérifier ce qui est affiché. */
function serveDashboard({ failing = [], delayFor = () => 0 }: Options = {}) {
  const requests: string[] = []
  const reply = (path: string, body: (url: URL) => object) =>
    http.get(apiUrl(path), async ({ request }) => {
      const url = new URL(request.url)
      requests.push(path + url.search)
      await delay(delayFor(url.searchParams.has("month") ? Number(url.searchParams.get("month")) : null))
      if (failing.includes(path)) return HttpResponse.json({ detail: "boom" }, { status: 500 })
      return HttpResponse.json(body(url))
    })
  server.use(
    reply("/analytics/budget", (url) => ({ month: Number(url.searchParams.get("month")), account_id: url.searchParams.get("account_id") })),
    reply("/analytics/expenses-by-category", () => ({ items: [{ category: "Courses", amount: 300 }] })),
    reply("/analytics/kpi-history", () => [{ month: 6 }]),
    reply("/analytics/top-merchants", () => ({ items: [{ merchant: "Carrefour" }] })),
    reply("/analytics/subscriptions", () => ({ items: [] })),
    reply("/analytics/timeseries", () => ({ salary_series: [{ v: 1 }], monthly_flows: [{ v: 2 }] })),
    reply("/analytics/patrimoine-allocation", () => ({ total: 10 })),
    reply("/analytics/budget-alerts", () => [{ category_id: 1 }]),
    reply("/analytics/insights", () => ({ items: [] })),
    reply("/analytics/sankey", () => ({ nodes: [], links: [] })),
    reply("/analytics/cashflow-projection", () => ({ points: [] })),
    reply("/analytics/tags", () => [{ tag: "Vacances" }]),
    reply("/month-review/closures", () => [
      { year: 2026, month: 5, highlight: "Déménagement" },
      { year: 2026, month: 4, highlight: null },
    ]),
    reply("/financial-events", () => [{ id: 1, date: "2026-06-01", title: "Nouveau job", note: null, account_id: null, account_name: null }]),
  )
  return requests
}

describe("useDashboardData", () => {
  it("charge les 14 blocs du mois et du compte demandés", async () => {
    const requests = serveDashboard()
    const { result } = renderHook(() => useDashboardData("3", 6, 2026), { wrapper })

    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(requests).toHaveLength(14)
    expect(requests).toContain("/analytics/budget?month=6&year=2026&account_id=3")
    expect(requests).toContain("/analytics/cashflow-projection?days=60&account_id=3")
    expect(requests).toContain("/analytics/patrimoine-allocation")
    expect(result.current.analytics).toEqual({ month: 6, account_id: "3" })
    expect(result.current.expensesByCategory).toEqual([{ category: "Courses", amount: 300 }])
    expect(result.current.salarySeries).toEqual([{ v: 1 }])
    expect(result.current.burnRateSeries).toEqual([{ v: 2 }])
    expect(result.current.milestones).toEqual([{ year: 2026, month: 5, highlight: "Déménagement" }])
    expect(result.current.events).toHaveLength(1)
    expect(result.current.failedCount).toBe(0)
  })

  it("« Tous les comptes » : aucun account_id dans les requêtes", async () => {
    const requests = serveDashboard()
    const { result } = renderHook(() => useDashboardData("all", 6, 2026), { wrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(requests.filter((r) => r.includes("account_id"))).toEqual([])
  })

  it("un endpoint en échec n'empêche pas les autres ; échec compté et signalé une seule fois", async () => {
    serveDashboard({ failing: ["/analytics/sankey", "/analytics/insights"] })
    const { result } = renderHook(() => useDashboardData("all", 6, 2026), { wrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.failedCount).toBe(2)
    expect(result.current.sankeyData).toBeNull()
    expect(result.current.insights).toBeNull()
    expect(result.current.analytics).toEqual({ month: 6, account_id: null })
    expect(result.current.topMerchants).toEqual([{ merchant: "Carrefour" }])
    expect(result.current.budgetAlerts).toEqual([{ category_id: 1 }])
    expect(await screen.findAllByText("Certaines données du tableau de bord n'ont pas pu être chargées.")).toHaveLength(1)
  })

  it("reload() relance tout et efface l'échec une fois l'endpoint revenu", async () => {
    const failing = ["/analytics/budget"]
    const requests = serveDashboard({ failing })
    const { result } = renderHook(() => useDashboardData("all", 6, 2026), { wrapper })
    await waitFor(() => expect(result.current.failedCount).toBe(1))

    failing.length = 0
    act(() => result.current.reload())

    await waitFor(() => expect(result.current.analytics).toEqual({ month: 6, account_id: null }))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.failedCount).toBe(0)
    expect(requests).toHaveLength(28)
  })

  it("enabled = false : aucune requête tant que le mois budgétaire n'est pas connu", async () => {
    const requests = serveDashboard()
    const { result, rerender } = renderHook(({ enabled }) => useDashboardData("all", 6, 2026, enabled), {
      wrapper,
      initialProps: { enabled: false },
    })

    await act(() => delay(20))
    expect(requests).toEqual([])
    rerender({ enabled: true })
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(requests).toHaveLength(14)
  })

  it("changement de mois : données vidées aussitôt, réponse de l'ancien mois ignorée", async () => {
    serveDashboard({ delayFor: (month) => (month === 5 ? 150 : 0) })
    const { result, rerender } = renderHook(({ month }) => useDashboardData("all", month, 2026), {
      wrapper,
      initialProps: { month: 5 },
    })

    rerender({ month: 6 })
    expect(result.current.analytics).toBeNull()
    await waitFor(() => expect(result.current.analytics).toEqual({ month: 6, account_id: null }))
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(() => delay(250))
    expect(result.current.analytics).toEqual({ month: 6, account_id: null })
    expect(result.current.loading).toBe(false)
  })

  it("changement de compte : les données du compte précédent ne restent pas affichées", async () => {
    serveDashboard({ delayFor: () => 30 })
    const { result, rerender } = renderHook(({ account }) => useDashboardData(account, 6, 2026), {
      wrapper,
      initialProps: { account: "1" },
    })
    await waitFor(() => expect(result.current.analytics).toEqual({ month: 6, account_id: "1" }))

    rerender({ account: "2" })

    expect(result.current.analytics).toBeNull()
    expect(result.current.topMerchants).toEqual([])
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.analytics).toEqual({ month: 6, account_id: "2" }))
  })

  it("reloadEvents() ne recharge que le journal", async () => {
    const requests = serveDashboard()
    const { result } = renderHook(() => useDashboardData("all", 6, 2026), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(() => result.current.reloadEvents())

    expect(requests).toHaveLength(15)
    expect(requests[requests.length - 1]).toBe("/financial-events")
  })
})
