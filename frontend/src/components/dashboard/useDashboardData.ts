import { useState, useEffect, useCallback } from "react"
import { toast } from "sonner"
import { api } from "@/lib/api"

export interface Milestone {
  year: number
  month: number
  highlight: string | null
}

/** Entrée du journal des décisions (`/financial-events`) */
export interface FinancialEvent {
  id: number
  date: string
  title: string
  note: string | null
  account_id: number | null
  account_name: string | null
}

/**
 * Charge toutes les données du tableau de bord pour un mois et un compte.
 *
 * - Une réponse arrivée après un changement de mois/compte est ignorée (sinon l'ancien mois
 *   écrasait le nouveau) et les données précédentes sont vidées dès le changement.
 * - Un échec n'empêche pas les autres blocs de se charger ; il est signalé une seule fois
 *   (`failedCount` + toast) et `reload()` relance tout.
 * - `enabled` permet d'attendre que le mois budgétaire soit connu avant la première charge.
 */
export function useDashboardData(selectedAccountId: string, month: number, year: number, enabled = true) {
  const [analytics, setAnalytics] = useState<any>(null)
  const [expensesByCategory, setExpensesByCategory] = useState<any[]>([])
  const [kpiHistory, setKpiHistory] = useState<any[]>([])
  const [milestones, setMilestones] = useState<Milestone[]>([])
  const [events, setEvents] = useState<FinancialEvent[]>([])
  const [topMerchants, setTopMerchants] = useState<any[]>([])
  const [subscriptions, setSubscriptions] = useState<any>(null)
  const [salarySeries, setSalarySeries] = useState<any[]>([])
  const [patrimoineAllocation, setPatrimoineAllocation] = useState<any>(null)
  const [burnRateSeries, setBurnRateSeries] = useState<any[]>([])
  const [budgetAlerts, setBudgetAlerts] = useState<any[]>([])
  const [insights, setInsights] = useState<any>(null)
  const [sankeyData, setSankeyData] = useState<any>(null)
  const [projection, setProjection] = useState<any>(null)
  const [tagTotals, setTagTotals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [failedCount, setFailedCount] = useState(0)
  const [reloadToken, setReloadToken] = useState(0)

  const reload = useCallback(() => setReloadToken(t => t + 1), [])
  // Après un ajout/une modification dans le journal : seul le journal est rechargé
  const reloadEvents = useCallback(async () => {
    try {
      setEvents(await api.get<FinancialEvent[]>("/financial-events"))
    } catch (e) {
      console.error("Error loading /financial-events:", e)
    }
  }, [])

  useEffect(() => {
    if (!enabled) return
    let cancelled = false

    // Données du mois précédent : on ne les laisse pas sous le libellé du nouveau mois
    setAnalytics(null)
    setExpensesByCategory([])
    setKpiHistory([])
    setTopMerchants([])
    setSubscriptions(null)
    setSalarySeries([])
    setBurnRateSeries([])
    setPatrimoineAllocation(null)
    setBudgetAlerts([])
    setInsights(null)
    setSankeyData(null)
    setProjection(null)
    setTagTotals([])
    setFailedCount(0)
    setLoading(true)

    const accId = selectedAccountId === "all" ? null : selectedAccountId
    const accParam = accId ? `&account_id=${accId}` : ""
    let failed = 0

    const safeLoad = async (url: string, setter: (data: any) => void) => {
      try {
        const data = await api.get<any>(url)
        if (!cancelled) setter(data)
      } catch (e: any) {
        console.error(`Error loading ${url}:`, e)
        failed += 1
      }
    }

    Promise.all([
      safeLoad(`/analytics/budget?month=${month}&year=${year}${accParam}`, setAnalytics),
      safeLoad(`/analytics/expenses-by-category?month=${month}&year=${year}${accParam}`, (d) => setExpensesByCategory(d?.items || [])),
      safeLoad(`/analytics/kpi-history?months_count=6${accParam}`, setKpiHistory),
      safeLoad(`/analytics/top-merchants?month=${month}&year=${year}${accParam}`, (d) => setTopMerchants(d?.items || [])),
      safeLoad(`/analytics/subscriptions?month=${month}&year=${year}${accParam}`, setSubscriptions),
      safeLoad(`/analytics/timeseries?year=${year}${accParam}`, (d) => {
        setSalarySeries(d?.salary_series || [])
        setBurnRateSeries(d?.monthly_flows || [])
      }),
      safeLoad("/analytics/patrimoine-allocation", setPatrimoineAllocation),
      safeLoad(`/analytics/budget-alerts?month=${month}&year=${year}${accParam}`, setBudgetAlerts),
      safeLoad(`/analytics/insights?month=${month}&year=${year}${accParam}`, setInsights),
      safeLoad(`/analytics/sankey?month=${month}&year=${year}${accParam}`, setSankeyData),
      safeLoad(`/analytics/cashflow-projection?days=60${accId ? `&account_id=${accId}` : ""}`, setProjection),
      safeLoad(`/analytics/tags?month=${month}&year=${year}${accParam}`, setTagTotals),
      // Faits marquants notés à la clôture des mois : jalons des courbes historiques
      safeLoad("/month-review/closures", (d: Milestone[]) => setMilestones((d || []).filter((c) => c.highlight))),
      // Journal des décisions : repères sur les mêmes courbes
      safeLoad("/financial-events", (d: FinancialEvent[]) => setEvents(d || [])),
    ]).then(() => {
      if (cancelled) return
      setLoading(false)
      setFailedCount(failed)
      if (failed > 0) toast.error("Certaines données du tableau de bord n'ont pas pu être chargées.")
    })

    return () => {
      cancelled = true
    }
  }, [month, year, selectedAccountId, enabled, reloadToken])

  return {
    analytics,
    expensesByCategory,
    kpiHistory,
    milestones,
    events,
    reloadEvents,
    topMerchants,
    subscriptions,
    salarySeries,
    patrimoineAllocation,
    burnRateSeries,
    budgetAlerts,
    insights,
    sankeyData,
    projection,
    tagTotals,
    loading,
    failedCount,
    reload,
  }
}
