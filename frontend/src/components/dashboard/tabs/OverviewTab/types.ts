import { type DrilldownScope } from "@/hooks/useDrilldown"

export const COLORS = ["#3b82f6", "#10b981", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#f59e0b", "#64748b"]

export interface OverviewTabProps {
  sankeyData: any
  expensesByCategory: any[]
  displayCurrency: string
  tagTotals: any[]
  patrimoineAllocation: any
  drilldownScope: DrilldownScope
}
