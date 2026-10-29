import { OverviewTabProps } from "./types"
import { useOverviewData } from "./useOverviewData"

/** Assemble l'état, les chargements et les actions de OverviewTab. */
export function useOverviewTab(sankeyData: OverviewTabProps["sankeyData"], expensesByCategory: OverviewTabProps["expensesByCategory"], displayCurrency: OverviewTabProps["displayCurrency"], tagTotals: OverviewTabProps["tagTotals"], patrimoineAllocation: OverviewTabProps["patrimoineAllocation"], drilldownScope: OverviewTabProps["drilldownScope"]) {
  const overviewData = useOverviewData({ sankeyData, expensesByCategory, displayCurrency, tagTotals, patrimoineAllocation, drilldownScope })
  return { sankeyData, expensesByCategory, displayCurrency, tagTotals, patrimoineAllocation, drilldownScope, ...overviewData }
}

export type OverviewTabCtx = ReturnType<typeof useOverviewTab>
