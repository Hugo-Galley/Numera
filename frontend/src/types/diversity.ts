import type { components } from "@/lib/api/generated/schema"
import type { ApiResponse } from "@/lib/api/types"

type Schemas = components["schemas"]

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

/** Pays ou secteur ; `market_pct` : poids de la référence de marché (null sans référence ou hors comparaison) */
export type BreakdownItem = Schemas["DiversityExposure"]

/** Alerte relative au marché : `overweight` (avec sa `dimension`), `correlated_block`, `redundant_pick`, `overlap` */
export type DiversityAlert = Omit<Schemas["DiversityAlert"], "type"> & { type: "danger" | "warning" | "info" }

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
  exposures: DiversityExposureGroup[]
  concentration: DiversityConcentration
  /** null : référence de marché introuvable (score neutre) */
  market: MarketComparison | null
  stock_picking: StockPickingLine[]
  coverage: DiversityCoverage
}

// --- Sur-exposition relative au marché (contrat étendu de /analytics/diversity-scanner) ---
// Dérivés du schéma généré (`make api-contract`) : un renommage côté backend casse `tsc`.

export type DiversityExposureGroup = Schemas["DiversityExposureGroup"]
/** `members` : noms des expositions du bloc */
export type CorrelatedBlock = Schemas["DiversityBlock"]
export type DiversityConcentration = Schemas["DiversityConcentration"]
export type MarketDimension = Schemas["DiversityMarketDimension"]
export type MarketDimensionKey = NonNullable<Schemas["DiversityAlert"]["dimension"]>
export type MarketComparison = Schemas["DiversityMarket"]
export type StockPickingLine = Schemas["DiversityStockPick"]
/** `composition_pct` : part de la valeur dont la composition est connue ; `with_prices_pct` : avec historique de cours */
export type DiversityCoverage = Schemas["DiversityCoverage"]
