export interface EtfHoldingItem {
  name: string
  ticker?: string
  weight: number
}

export interface EtfProfile {
  id: number
  name: string
  ticker: string
  isin?: string
  aliases: string[]
  countries: Record<string, number>
  sectors: Record<string, number>
  top_holdings: EtfHoldingItem[]
  is_system: boolean
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
}

export interface MarketSearchResult {
  symbol: string
  name: string
  isin?: string
  type: string
  exchange?: string
  currency: string
  etf_profile_id?: number
  is_custom_etf?: boolean
}

export interface HoldingSuggestion {
  name: string
  ticker: string
  isin?: string
  historical_net_invested: number
  tx_count: number
  etf_profile_id?: number
  is_etf: boolean
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
  holdings: any[]
}
