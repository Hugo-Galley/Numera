import type { ApiResponse } from "@/lib/api/types"

export type CompositionField = "countries" | "sectors" | "top_holdings"
// yahoo : actualisé depuis Yahoo Finance · preset : préréglage intégré · manual : saisi à la main
export type CompositionSource = "yahoo" | "preset" | "manual"

export interface EtfCompositionInfo {
  profile_id: number
  profile_name: string
  tickers: string[]
  value_eur: number
  sources: Partial<Record<CompositionField, CompositionSource>>
  refreshed_at?: string | null
}

export interface PortfolioHolding {
  id: number
  account_id: number
  ticker: string
  isin?: string
  asset_name: string
  quantity: number
  buy_price_avg?: number
  currency: string
  etf_profile_id?: number
  current_price?: number
  current_price_eur?: number
  current_value_eur?: number
  total_invested_eur?: number
  gain_eur?: number
  gain_pct?: number
  is_etf: boolean
  quote_currency?: string
  price_date?: string
  price_stale?: boolean
  pays_dividends?: boolean | null
  dividends_received_eur?: number
  dividends_12m_eur?: number
  last_dividend_date?: string | null
  total_return_eur?: number | null
  total_return_pct?: number | null
}

export interface UnderlyingCompanySource {
  source: string
  pct_in_source: number
  value_eur: number
}

export interface UnderlyingCompany {
  name: string
  ticker?: string
  direct_value_eur: number
  indirect_value_eur: number
  total_value_eur: number
  pct_stocks: number
  pct_total_wealth: number
  sources: UnderlyingCompanySource[]
  has_overlap: boolean
}

export interface BreakdownItem {
  name: string
  value_eur: number
  percentage_stocks: number
  percentage_total_wealth: number
}

export interface DiversityAlert {
  type: "danger" | "warning" | "info"
  category: "company" | "country" | "sector" | "overlap"
  title: string
  message: string
  item_name?: string
  value_pct?: number
}

export interface DiversityScannerResponse {
  score: number
  score_label: string
  totals: {
    stocks_eur: number
    epargne_eur: number
    courant_eur: number
    fonds_euros_eur: number
    other_eur: number
    wealth_eur: number
    holdings_count: number
    etfs_count: number
  }
  top_underlying_companies: UnderlyingCompany[]
  countries: BreakdownItem[]
  sectors: BreakdownItem[]
  alerts: DiversityAlert[]
  holdings: ApiResponse<"/analytics/diversity-scanner", "get">["holdings"]
  etf_compositions: EtfCompositionInfo[]
}
