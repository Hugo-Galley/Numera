

export type Kind = "pea" | "per" | "cto" | "assurance_vie" | "livret_a" | "livret_jeune" | "pee" | "ldds" | "lep"

export interface WrapperCard {
  kind: Kind
  account_id: number
  account_name: string
  opened_at: string | null
  current: number | null
  ceiling: number | null
  remaining: number | null
  used_pct: number | null
  age_years: number | null
  milestone_years: number | null
  milestone_reached: boolean | null
  estimated_tax_saving: number | null
  allowance: number | null
  total_contributed: number | null
  blocked: number | null
  available: number | null
  next_unlock_date: string | null
  alerts: string[]
}

export interface TaxSettings {
  tmi_pct: number
  prior_year_pro_income: number
  household: "single" | "couple"
  gross_annual_salary: number
}

export interface WrapperSuggestion {
  account_id: number
  account_name: string
  kind: Kind
}

export interface AllocationAdvice {
  rank: number
  kind: Kind
  account_id: number | null
  account_name: string | null
  reason: string
  remaining: number | null
}

export interface TaxOverview {
  year: number
  settings: TaxSettings
  wrappers: WrapperCard[]
  suggestions: WrapperSuggestion[]
  allocation_advice: AllocationAdvice[]
  precaution_months: number | null
}

export interface CtoYearRow {
  account_id: number
  account_name: string
  dividends_gross_eur: number
  dividends_net_eur: number
  withholding_eur: number
  realized_eur: number
  proceeds_eur: number
  sales: number
  unknown_cost_sales: number
}

export interface AnnualReport {
  year: number
  pfu_rate_dividends: number
  pfu_rate_gains: number
  accounts: CtoYearRow[]
  box_2dc: number
  box_3vg: number
  box_3vh: number
  estimated_pfu_eur: number
  warnings: string[]
}

export const KIND_LABELS: Record<Kind, string> = {
  pea: "PEA",
  per: "PER",
  cto: "CTO",
  assurance_vie: "Assurance-vie",
  livret_a: "Livret A",
  livret_jeune: "Livret Jeune",
  pee: "PEE",
  ldds: "LDDS",
  lep: "LEP",
}

export const TMI_OPTIONS = [0, 11, 30, 41, 45]
