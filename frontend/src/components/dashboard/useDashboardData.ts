import i18n from "i18next"
import { useState, useEffect, useCallback } from "react"
import { toast } from "sonner"
import { resetApiCache } from "@/lib/apiCache"
import {
  getAnalyticsBudget, getAnalyticsBudgetAlerts, getAnalyticsCashflowProjection, getAnalyticsExpensesByCategory, getAnalyticsInsights,
  getAnalyticsKpiHistory, getAnalyticsPatrimoineAllocation, getAnalyticsSankey, getAnalyticsSubscriptions, getAnalyticsTags,
  getAnalyticsTimeseries, getAnalyticsTopMerchants, getFinancialEvents,
} from "@/lib/api/analytics"
import { getMonthReviewClosures } from "@/lib/api/monthReview"
import type { BudgetAlert, BudgetOverview, CashflowProjection, ExpensesByCategory, Insights, KpiHistoryPoint, PatrimoineAllocation, SankeyData, SubscriptionsData, TagSpending, Timeseries, TopMerchants } from "./types"

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
  const [analytics, setAnalytics] = useState<BudgetOverview | null>(null)
  const [expensesByCategory, setExpensesByCategory] = useState<ExpensesByCategory["items"]>([])
  const [kpiHistory, setKpiHistory] = useState<KpiHistoryPoint[]>([])
  const [milestones, setMilestones] = useState<Milestone[]>([])
  const [events, setEvents] = useState<FinancialEvent[]>([])
  const [topMerchants, setTopMerchants] = useState<TopMerchants["items"]>([])
  const [subscriptions, setSubscriptions] = useState<SubscriptionsData | null>(null)
  const [salarySeries, setSalarySeries] = useState<NonNullable<Timeseries["salary_series"]>>([])
  const [patrimoineAllocation, setPatrimoineAllocation] = useState<PatrimoineAllocation | null>(null)
  const [burnRateSeries, setBurnRateSeries] = useState<NonNullable<Timeseries["monthly_flows"]>>([])
  const [budgetAlerts, setBudgetAlerts] = useState<BudgetAlert[]>([])
  const [insights, setInsights] = useState<Insights | null>(null)
  const [sankeyData, setSankeyData] = useState<SankeyData | null>(null)
  const [projection, setProjection] = useState<CashflowProjection | null>(null)
  const [tagTotals, setTagTotals] = useState<TagSpending[]>([])
  const [loading, setLoading] = useState(true)
  const [failedCount, setFailedCount] = useState(0)
  const [reloadToken, setReloadToken] = useState(0)

  // Rechargement demandé : on contourne le cache de lecture
  const reload = useCallback(() => {
    resetApiCache()
    setReloadToken(t => t + 1)
  }, [])
  // Après un ajout/une modification dans le journal : seul le journal est rechargé
  const reloadEvents = useCallback(async () => {
    resetApiCache()
    try {
      setEvents(await getFinancialEvents<FinancialEvent[]>())
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

    // `label` ne sert qu'au journal d'erreur : la requête est celle du wrapper de lib/api
    const safeLoad = async (label: string, load: () => Promise<any>, setter: (data: any) => void) => {
      try {
        const data = await load()
        if (!cancelled) setter(data)
      } catch (e) {
        console.error(`Error loading ${label}:`, e)
        failed += 1
      }
    }

    Promise.all([
      safeLoad("budget", () => getAnalyticsBudget(`?month=${month}&year=${year}${accParam}`), setAnalytics),
      safeLoad("expenses-by-category", () => getAnalyticsExpensesByCategory(`?month=${month}&year=${year}${accParam}`), (d) => setExpensesByCategory(d?.items || [])),
      safeLoad("kpi-history", () => getAnalyticsKpiHistory(`?months_count=6${accParam}`), setKpiHistory),
      safeLoad("top-merchants", () => getAnalyticsTopMerchants(`?month=${month}&year=${year}${accParam}`), (d) => setTopMerchants(d?.items || [])),
      safeLoad("subscriptions", () => getAnalyticsSubscriptions(`?month=${month}&year=${year}${accParam}`), setSubscriptions),
      safeLoad("timeseries", () => getAnalyticsTimeseries(`?year=${year}${accParam}`), (d) => {
        setSalarySeries(d?.salary_series || [])
        setBurnRateSeries(d?.monthly_flows || [])
      }),
      safeLoad("patrimoine-allocation", () => getAnalyticsPatrimoineAllocation(), setPatrimoineAllocation),
      safeLoad("budget-alerts", () => getAnalyticsBudgetAlerts(`?month=${month}&year=${year}${accParam}`), setBudgetAlerts),
      safeLoad("insights", () => getAnalyticsInsights(`?month=${month}&year=${year}${accParam}`), setInsights),
      safeLoad("sankey", () => getAnalyticsSankey(`?month=${month}&year=${year}${accParam}`), setSankeyData),
      safeLoad("cashflow-projection", () => getAnalyticsCashflowProjection(`?days=60${accId ? `&account_id=${accId}` : ""}`), setProjection),
      safeLoad("tags", () => getAnalyticsTags(`?month=${month}&year=${year}${accParam}`), setTagTotals),
      // Faits marquants notés à la clôture des mois : jalons des courbes historiques
      safeLoad("month-review/closures", () => getMonthReviewClosures(), (d: Milestone[]) => setMilestones((d || []).filter((c) => c.highlight))),
      // Journal des décisions : repères sur les mêmes courbes
      safeLoad("financial-events", () => getFinancialEvents(), (d: FinancialEvent[]) => setEvents(d || [])),
    ]).then(() => {
      if (cancelled) return
      setLoading(false)
      setFailedCount(failed)
      if (failed > 0) toast.error(i18n.t("partialLoadError", { ns: "dashboard" }))
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
