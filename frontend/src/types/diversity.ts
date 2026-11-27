import type { ApiResponse } from "@/lib/api/types"

export type CompositionField = "countries" | "sectors" | "top_holdings"
// Émetteurs (ishares, amundi, spdr), replis justetf et yahoo ; manual : saisi à la main
export type CompositionSource = "ishares" | "amundi" | "spdr" | "justetf" | "yahoo" | "manual"

export interface EtfCompositionInfo {
  profile_id: number
  profile_name: string
  tickers: string[]
  value_eur: number
  sources: Partial<Record<CompositionField, CompositionSource>>
  refreshed_at?: string | null
  // Données utilisées (celles de l'ETF de référence pour un synthétique)
  provider?: string | null
  composition_as_of?: string | null
  coverage_pct?: number | null
  lines_count?: number
  // Fonds détenu
  replication?: string
  index_name?: string | null
  exposure_profile_id?: number | null
  exposure_profile_name?: string | null
}

export interface PortfolioHolding {
  id: number
  account_id: number
  ticker: string
  isin?: string
  isin_missing?: boolean
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
  /** Poids de la référence de marché (pays et secteurs) */
  market_pct?: number | null
}

export interface DiversityAlert {
  type: "danger" | "warning" | "info"
  category: "company" | "country" | "sector" | "overlap" | "overweight" | "redundant_pick" | "correlated_block"
  /** Dimension d'une alerte « overweight » */
  dimension?: MarketDimensionKey | null
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
    direct_eur: number
    etf_eur: number
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
  exposures?: DiversityExposureGroup[]
  concentration?: DiversityConcentration
  /** null : référence de marché introuvable */
  market?: MarketComparison | null
  stock_picking?: StockPickingLine[]
  coverage?: DiversityCoverage
}

// --- Sur-exposition relative au marché (contrat étendu de /analytics/diversity-scanner) ---
// Types écrits à la main d'après la spec (« Contrat de l'API ») tant que le schéma généré ne les porte pas ;
// tous facultatifs pour rester compatibles avec une réponse plus ancienne.

export type ExposureKind = "fund" | "direct" | "crypto"
export type PairSource = "prices" | "composition" | "unknown"

export interface ExposureSupport {
  account_id?: number
  account_name?: string
  ticker: string
  value_eur: number
}

export interface DiversityExposureGroup {
  id: string
  name: string
  kind: ExposureKind
  value_eur: number
  weight_pct: number
  supports: ExposureSupport[]
}

export interface CorrelatedBlock {
  /** Noms des expositions du bloc */
  members: string[]
  weight_pct: number
  mean_rho: number
}

export interface DiversityConcentration {
  effective_bets: number
  exposures_count: number
  blocks: CorrelatedBlock[]
  pairs_by_source?: Partial<Record<PairSource, number>>
}

export interface MarketGapRow {
  name: string
  portfolio_pct: number
  market_pct: number
  /** Société absente du top de la référence : market_pct est un majorant */
  market_pct_is_upper_bound: boolean
  gap_pts: number
}

export interface MarketDimension {
  active_share_pct: number
  covered_pct?: number
  rows: MarketGapRow[]
}

export type MarketDimensionKey = "companies" | "sectors" | "countries"

export interface MarketComparison {
  name: string
  ticker?: string | null
  companies: MarketDimension
  sectors: MarketDimension
  countries: MarketDimension
}

export interface StockPickingLine {
  name: string
  ticker?: string
  value_eur?: number
  indirect_value_eur: number
  correlation_with_core: number | null
  source: PairSource
  redundant: boolean
}

export interface DiversityCoverage {
  /** Part de la valeur dont la composition est connue */
  composition_pct?: number
  /** Part des expositions avec un historique de cours */
  with_prices_pct?: number
}

export interface MarketReferenceSetting {
  ticker: string | null
}
