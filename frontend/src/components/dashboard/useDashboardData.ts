import { useState, useEffect } from "react"
import { api } from "@/lib/api"

export function useDashboardData(selectedAccountId: string, month: number, year: number) {
  const [analytics, setAnalytics] = useState<any>(null)
  const [expensesByCategory, setExpensesByCategory] = useState<any[]>([])
  const [kpiHistory, setKpiHistory] = useState<any[]>([])
  const [topMerchants, setTopMerchants] = useState<any[]>([])
  const [subscriptions, setSubscriptions] = useState<any>(null)
  const [salarySeries, setSalarySeries] = useState<any[]>([])
  const [investments, setInvestments] = useState<any>(null)
  const [allocation, setAllocation] = useState<any>(null)
  const [patrimoineAllocation, setPatrimoineAllocation] = useState<any>(null)
  const [burnRateSeries, setBurnRateSeries] = useState<any[]>([])
  const [budgetAlerts, setBudgetAlerts] = useState<any[]>([])
  const [insights, setInsights] = useState<any>(null)
  const [sankeyData, setSankeyData] = useState<any>(null)
  const [projection, setProjection] = useState<any>(null)
  const [tagTotals, setTagTotals] = useState<any[]>([])

  useEffect(() => {
    async function loadData() {
      const accId = selectedAccountId === "all" ? null : selectedAccountId
      const accParam = accId ? `&account_id=${accId}` : ""

      const safeLoad = async (url: string, setter: (data: any) => void) => {
        try {
          const data = await api.get<any>(url)
          setter(data)
        } catch (e: any) {
          console.error(`Error loading ${url}:`, e)
          if (e.message === "An error occurred") {
             console.warn(`Endpoint ${url} returned a generic 500 error. Check backend logs.`)
          }
        }
      }

      safeLoad(`/analytics/budget?month=${month}&year=${year}${accParam}`, setAnalytics)
      safeLoad(`/analytics/expenses-by-category?month=${month}&year=${year}${accParam}`, (d) => setExpensesByCategory(d?.items || []))
      safeLoad(`/analytics/kpi-history?months_count=6${accParam}`, setKpiHistory)
      safeLoad(`/analytics/top-merchants?month=${month}&year=${year}${accParam}`, (d) => setTopMerchants(d?.items || []))
      safeLoad(`/analytics/subscriptions?month=${month}&year=${year}${accParam}`, setSubscriptions)
      safeLoad(`/analytics/timeseries?year=${year}${accParam}`, (d) => {
        setSalarySeries(d?.salary_series || [])
        setBurnRateSeries(d?.monthly_flows || [])
      })
      safeLoad(`/analytics/investments?month=${month}&year=${year}${accParam}`, setInvestments)
      safeLoad(`/analytics/investments-allocation${accId ? `?account_id=${accId}` : ""}`, setAllocation)
      safeLoad("/analytics/patrimoine-allocation", setPatrimoineAllocation)
      safeLoad(`/analytics/budget-alerts?month=${month}&year=${year}${accParam}`, setBudgetAlerts)
      safeLoad(`/analytics/insights?month=${month}&year=${year}${accParam}`, setInsights)
      safeLoad(`/analytics/sankey?month=${month}&year=${year}${accParam}`, setSankeyData)
      safeLoad(`/analytics/cashflow-projection?days=60${accId ? `&account_id=${accId}` : ""}`, setProjection)
      safeLoad(`/analytics/tags?month=${month}&year=${year}${accParam}`, setTagTotals)
    }
    loadData()
  }, [month, year, selectedAccountId])

  return {
    analytics,
    expensesByCategory,
    kpiHistory,
    topMerchants,
    subscriptions,
    salarySeries,
    investments,
    allocation,
    patrimoineAllocation,
    burnRateSeries,
    budgetAlerts,
    insights,
    sankeyData,
    projection,
    tagTotals
  }
}
