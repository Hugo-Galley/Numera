import { type DrilldownScope } from "@/hooks/useDrilldown"
import type { ExpensesByCategory, PatrimoineAllocation, SankeyData, TagSpending } from "../../types"

export const COLORS = ["#3b82f6", "#10b981", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#f59e0b", "#64748b"]

export interface OverviewTabProps {
  sankeyData: SankeyData | null
  expensesByCategory: ExpensesByCategory["items"]
  displayCurrency: string
  tagTotals: TagSpending[]
  patrimoineAllocation: PatrimoineAllocation | null
  drilldownScope: DrilldownScope
}
