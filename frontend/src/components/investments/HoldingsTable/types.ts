import { PortfolioHolding } from "@/types/diversity"

export type TypeFilter = "all" | "action" | "etf"
export type PerfFilter = "all" | "gain" | "loss"

export interface HoldingsTableProps {
  accountId: number
  accountName: string
  holdings: PortfolioHolding[]
  onRefresh: () => void
  onAddDividend?: (holding: PortfolioHolding) => void
}
