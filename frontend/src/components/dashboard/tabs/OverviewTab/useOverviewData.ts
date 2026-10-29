import { useDrilldown } from "@/hooks/useDrilldown"
import { useIsMobile } from "@/hooks/useIsMobile"
import { useMemo, useState } from "react"
import { COLORS, OverviewTabProps } from "./types"

/** Regroupements du patrimoine (compte, catégorie, mixte, établissement) et données des graphiques. */
export function useOverviewData(p: { sankeyData: OverviewTabProps["sankeyData"]; expensesByCategory: OverviewTabProps["expensesByCategory"]; displayCurrency: OverviewTabProps["displayCurrency"]; tagTotals: OverviewTabProps["tagTotals"]; patrimoineAllocation: OverviewTabProps["patrimoineAllocation"]; drilldownScope: OverviewTabProps["drilldownScope"] }) {
  const { sankeyData, expensesByCategory, displayCurrency, tagTotals, patrimoineAllocation, drilldownScope } = p
  const isMobile = useIsMobile()
  const { openDrilldown } = useDrilldown()
  const openCategory = (item: any) =>
    item?.category && openDrilldown({ ...drilldownScope, label: item.category.name, categoryId: item.category.id ?? null })
  const [groupBy, setGroupBy] = useState<"account" | "category" | "mixed" | "institution">("mixed")

  const flatItems = useMemo(() => {
    if (!patrimoineAllocation?.items) return []
    const total = patrimoineAllocation.total_patrimoine || 1
    return patrimoineAllocation.items.map((item: any, i: number) => ({
      id: `${item.account_id}-${item.account_name}`,
      name: item.account_name,
      type: item.type,
      balance_eur: item.balance_eur,
      percentage: Number(((item.balance_eur / total) * 100).toFixed(2)),
      color: COLORS[i % COLORS.length],
      original_item: item
    }))
  }, [patrimoineAllocation])

  const groupedItems = useMemo(() => {
    if (!patrimoineAllocation?.items) return {}
    const groups: Record<string, { total_eur: number; items: any[] }> = {
      courant: { total_eur: 0, items: [] },
      epargne: { total_eur: 0, items: [] },
      investissement: { total_eur: 0, items: [] }
    }
    
    patrimoineAllocation.items.forEach((item: any) => {
      const type = item.type || "courant"
      if (!groups[type]) {
        groups[type] = { total_eur: 0, items: [] }
      }
      groups[type].items.push(item)
      groups[type].total_eur += item.balance_eur
    })
    
    return groups
  }, [patrimoineAllocation])

  const CATEGORY_COLORS: Record<string, string> = {
    courant: "#3b82f6", // Blue
    epargne: "#10b981", // Emerald
    investissement: "#6366f1" // Indigo
  }

  const CATEGORY_LABELS: Record<string, string> = {
    courant: "Comptes Courants",
    epargne: "Épargne",
    investissement: "Investissements"
  }

  const categoryData = useMemo(() => {
    const total = patrimoineAllocation?.total_patrimoine || 0
    return [
      {
        name: "Comptes Courants",
        type: "courant",
        value: groupedItems.courant?.total_eur || 0,
        percentage: total > 0 ? Number(((groupedItems.courant?.total_eur || 0) / total * 100).toFixed(2)) : 0,
        color: CATEGORY_COLORS.courant,
      },
      {
        name: "Épargne",
        type: "epargne",
        value: groupedItems.epargne?.total_eur || 0,
        percentage: total > 0 ? Number(((groupedItems.epargne?.total_eur || 0) / total * 100).toFixed(2)) : 0,
        color: CATEGORY_COLORS.epargne,
      },
      {
        name: "Investissements",
        type: "investissement",
        value: groupedItems.investissement?.total_eur || 0,
        percentage: total > 0 ? Number(((groupedItems.investissement?.total_eur || 0) / total * 100).toFixed(2)) : 0,
        color: CATEGORY_COLORS.investissement,
      },
    ].filter(cat => cat.value > 0)
  }, [groupedItems, patrimoineAllocation])

  const mixedItems = useMemo(() => {
    if (!patrimoineAllocation?.items) return []
    
    let totalCourant = 0
    let totalEpargne = 0
    const list: any[] = []
    
    patrimoineAllocation.items.forEach((item: any) => {
      if (item.type === "courant") {
        totalCourant += item.balance_eur
      } else if (item.type === "epargne") {
        totalEpargne += item.balance_eur
      } else {
        list.push({
          id: `${item.account_id}-${item.account_name}`,
          name: item.account_name,
          type: item.type,
          balance_eur: item.balance_eur,
          original_item: item
        })
      }
    })
    
    const result: any[] = []
    if (totalCourant > 0) {
      result.push({
        id: "group-courant",
        name: "Comptes Courants",
        type: "courant",
        balance_eur: totalCourant,
        isGroup: true,
        color: "#3b82f6" // blue
      })
    }
    
    if (totalEpargne > 0) {
      result.push({
        id: "group-epargne",
        name: "Épargne",
        type: "epargne",
        balance_eur: totalEpargne,
        isGroup: true,
        color: "#10b981" // emerald
      })
    }
    
    list.forEach((item, index) => {
      item.color = COLORS[(index + 2) % COLORS.length]
      result.push(item)
    })
    
    const total = patrimoineAllocation.total_patrimoine || 1
    result.forEach(item => {
      item.percentage = Number(((item.balance_eur / total) * 100).toFixed(2))
    })
    
    result.sort((a, b) => b.balance_eur - a.balance_eur)
    
    return result
  }, [patrimoineAllocation])

  const institutionData = useMemo(() => {
    if (!patrimoineAllocation?.items) return []
    const total = patrimoineAllocation.total_patrimoine || 1
    
    // Group accounts by institution name
    const grouped: Record<string, { name: string; value: number; items: any[] }> = {}
    
    patrimoineAllocation.items.forEach((item: any) => {
      const instName = item.institution ? item.institution.trim() : "Autre / Non spécifié"
      if (!grouped[instName]) {
        grouped[instName] = {
          name: instName,
          value: 0,
          items: []
        }
      }
      grouped[instName].value += item.balance_eur
      grouped[instName].items.push(item)
    })
    
    // Convert to array and calculate percentage & color
    return Object.values(grouped)
      .sort((a, b) => b.value - a.value)
      .map((group, index) => ({
        ...group,
        percentage: Number(((group.value / total) * 100).toFixed(2)),
        color: COLORS[index % COLORS.length]
      }))
  }, [patrimoineAllocation])

  const chartData = 
    groupBy === "category" 
      ? categoryData 
      : groupBy === "account" 
      ? flatItems 
      : groupBy === "institution" 
      ? institutionData 
      : mixedItems

  const chartDataKey = groupBy === "category" || groupBy === "institution" ? "value" : "balance_eur"

  return { isMobile, openDrilldown, openCategory, groupBy, setGroupBy, flatItems, groupedItems, CATEGORY_COLORS, CATEGORY_LABELS, categoryData, mixedItems, institutionData, chartData, chartDataKey }
}
