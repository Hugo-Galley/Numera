import { DiversityScannerResponse } from "@/types/diversity"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { useEffect, useState } from "react"
import { useIsMobile } from "@/hooks/useIsMobile"
import { useNavigate } from "react-router-dom"

/** Chargement des allocations et du scanner de diversité, drill-down et données du graphique. */
export function useInvestmentsData() {
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const [allocation, setAllocation] = useState<any>(null)
  const [advancedAllocation, setAdvancedAllocation] = useState<any>(null)
  const [diversity, setDiversity] = useState<DiversityScannerResponse | null>(null)
const [loading, setLoading] = useState(true)
  const [drillDown, setDrillDown] = useState<{ title: string, items: any[] } | null>(null)
  const [refreshingCompositions, setRefreshingCompositions] = useState(false)

  const refreshCompositions = async () => {
    setRefreshingCompositions(true)
    try {
      const res = await api.post<{ refreshed: number }>("/etf-profiles/refresh-held", {})
      const div = await api.get<DiversityScannerResponse>("/analytics/diversity-scanner")
      if (div && div.totals.holdings_count > 0) setDiversity(div)
      toast.success(`${res.refreshed} composition${res.refreshed > 1 ? "s" : ""} actualisée${res.refreshed > 1 ? "s" : ""} depuis Yahoo`)
    } catch {
      toast.error("Impossible d'actualiser les compositions")
    } finally {
      setRefreshingCompositions(false)
    }
  }

  useEffect(() => {
    async function loadData() {
      try {
        const [basic, advanced] = await Promise.all([
          api.get("/analytics/investments-allocation"),
          api.get("/analytics/investments-allocation-advanced")
        ])
        setAllocation(basic)
        setAdvancedAllocation(advanced)
        // Load diversity data separately (non-blocking, may have no holdings)
        try {
          const div = await api.get<DiversityScannerResponse>("/analytics/diversity-scanner")
          if (div && div.totals.holdings_count > 0) setDiversity(div)
        } catch { /* No holdings yet, that's fine */ }
      } catch (error) {
        toast.error("Erreur lors du chargement de l'allocation")
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const handleAccountClick = (accountId: number) => {
    navigate(`/accounts/${accountId}`)
  }

  const getDrilldownItems = (clickedData: any) => {
    if (!clickedData) return []
    if (Array.isArray(clickedData.items)) return clickedData.items
    if (clickedData.payload && Array.isArray(clickedData.payload.items)) return clickedData.payload.items
    if (clickedData.payload?.payload && Array.isArray(clickedData.payload.payload.items)) return clickedData.payload.payload.items
    return []
  }

  const getDrilldownTitle = (prefix: string, clickedData: any) => {
    if (!clickedData) return prefix
    const name = clickedData.name || clickedData.payload?.name || clickedData.payload?.payload?.name || ""
    return `${prefix} : ${name}`
  }

  const chartData = (allocation?.items || []).map((item: any) => ({
    name: item.account_name,
    value: item.current_value,
    percentage: item.percentage,
    id: item.account_id
  }))

  return { navigate, isMobile, allocation, setAllocation, advancedAllocation, setAdvancedAllocation, diversity, setDiversity, loading, setLoading, drillDown, setDrillDown, refreshingCompositions, setRefreshingCompositions, refreshCompositions, handleAccountClick, getDrilldownItems, getDrilldownTitle, chartData }
}
