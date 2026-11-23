import { OverviewTabProps } from "./types"
import { useOverviewTab } from "./useOverviewTab"
import { SankeyCard } from "./SankeyCard"
import { WealthAllocationCard } from "./WealthAllocationCard"
import { ExpensesCards } from "./ExpensesCards"
import { TagTotalsCard } from "./TagTotalsCard"

export function OverviewTab({
  sankeyData,
  expensesByCategory,
  displayCurrency,
  tagTotals,
  patrimoineAllocation,
  drilldownScope,
  incomePending = false,
}: OverviewTabProps) {
  const ctx = useOverviewTab(sankeyData, expensesByCategory, displayCurrency, tagTotals, patrimoineAllocation, drilldownScope)
  return (
    <div className="space-y-5 md:space-y-8">
      <SankeyCard ctx={ctx} incomePending={incomePending} />

      <WealthAllocationCard ctx={ctx} />

      <ExpensesCards ctx={ctx} />

      <TagTotalsCard ctx={ctx} />
    </div>
  )
}
