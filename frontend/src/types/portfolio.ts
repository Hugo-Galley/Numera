export interface PortfolioReconciliationPoint {
  date: string
  snapshot_value: number
  computed_value: number
  gap: number
  gap_pct: number | null
  flagged: boolean
}

export interface PortfolioRealizedYear {
  year: number
  realized_eur: number
  proceeds_eur: number
  sales: number
}

export interface PortfolioRead {
  account_id: number
  account_name: string
  currency: string
  valued_by_positions: boolean
  value_source: "positions" | "snapshot"
  baseline_date: string | null
  value: number
  value_eur: number
  positions_value_eur: number
  cash: number
  net_invested: number
  net_invested_eur: number
  gain: number
  gain_eur: number
  performance_pct: number | null
  xirr_pct: number | null
  twr_pct: number | null
  period_days: number
  unrealized_eur: number | null
  unrealized_pct: number | null
  fx_effect_eur: number | null
  /** Part de la plus-value latente due à la décote d'achat (cours de référence saisi) */
  discount_eur?: number | null
  /** Part due au cours depuis l'achat (plus-value latente − décote) */
  market_gain_eur?: number | null
  lines_without_cost: string[]
  realized_eur: number
  realized_unknown_sales: number
  realized_by_year: PortfolioRealizedYear[]
  dividends_eur: number
  dividends_12m_eur: number
  withholding_eur: number
  fees_eur: number
  stale_tickers: string[]
  snapshot: { date: string; value: number } | null
  reconciliation: PortfolioReconciliationPoint[] | null
  warnings: string[]
}

