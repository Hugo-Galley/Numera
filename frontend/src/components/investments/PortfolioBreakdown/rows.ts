/** Lignes du donut selon la vue (entreprises, positions, secteurs, pays) et la provenance (tout, en direct, via ETF). */
import { countryName } from "@/lib/countries"
import type { BreakdownRow } from "./slices"

export type BreakdownView = "companies" | "positions" | "sectors" | "countries"
export type BreakdownSource = "all" | "direct" | "etf"

/** Champs lus dans la réponse de `/analytics/diversity-scanner` (compte seul ou tous les comptes). */
export interface BreakdownData {
  totals: { stocks_eur: number; direct_eur: number; etf_eur: number; holdings_count: number; etfs_count: number }
  top_underlying_companies: {
    name: string
    ticker?: string | null
    total_value_eur: number
    direct_value_eur: number
    indirect_value_eur: number
    has_overlap: boolean
  }[]
  holdings: { name?: string | null; ticker: string; value_eur: number; etf_profile_id?: number | null }[]
  sectors: { name: string; value_eur: number }[]
  countries: { name: string; value_eur: number }[]
}

/** Secteurs et pays dès que le scanner en donne (les actions en direct ont les leurs), les positions à partir de deux lignes. */
export function viewsFor(data: BreakdownData): BreakdownView[] {
  const views: BreakdownView[] = ["companies"]
  if (data.holdings.length > 1) views.push("positions")
  for (const view of ["sectors", "countries"] as const) if (data[view].some((row) => row.value_eur > 0)) views.push(view)
  return views
}

/** Le choix de provenance n'apparaît que s'il y a à la fois des lignes en direct et des ETF, pour entreprises et positions. */
export function hasSourceChoice(data: BreakdownData, view: BreakdownView): boolean {
  return (view === "companies" || view === "positions") && data.totals.direct_eur > 0 && data.totals.etf_eur > 0
}

/** Valeur couverte par la vue : toutes les positions, ou seulement la part en direct / via ETF. */
export function totalFor(data: BreakdownData, source: BreakdownSource): number {
  if (source === "direct") return data.totals.direct_eur
  if (source === "etf") return data.totals.etf_eur
  return data.totals.stocks_eur
}

const COMPANY_VALUE: Record<BreakdownSource, (c: BreakdownData["top_underlying_companies"][number]) => number> = {
  all: (c) => c.total_value_eur,
  direct: (c) => c.direct_value_eur,
  etf: (c) => c.indirect_value_eur,
}

export function rowsFor(data: BreakdownData, view: BreakdownView, source: BreakdownSource): BreakdownRow[] {
  switch (view) {
    case "companies":
      return data.top_underlying_companies.map((c) => ({
        name: c.name,
        value: COMPANY_VALUE[source](c),
        ticker: c.ticker,
        // Un doublon n'a de sens que sur la vue complète
        overlap: source === "all" && c.has_overlap,
      }))
    case "positions":
      return data.holdings
        // Même règle que `look_through` : une position avec un profil ETF est décomposée, les autres (cryptos comprises)
        // sont en direct. La réponse ne donne pas le type de cotation : `etf_profile_id` seul décide.
        .filter((h) => source === "all" || (source === "etf") === (h.etf_profile_id != null))
        .map((h) => ({ name: h.name || h.ticker, value: h.value_eur, ticker: h.ticker }))
    case "sectors":
      return data.sectors.map((s) => ({ name: s.name, value: s.value_eur }))
    case "countries":
      // `countryName` rend tel quel ce qui n'est pas un code : « Liquidités et dérivés » et « Crypto-actifs » sont des
      // parts nommées ; « Autres » et « Non renseigné » sont regroupés dans la part « Autres pays »
      return data.countries.map((c) => ({ name: countryName(c.name), value: c.value_eur }))
  }
}
