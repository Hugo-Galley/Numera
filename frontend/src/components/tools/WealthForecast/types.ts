

export interface ForecastPoint {
  year: number
  base: number
  boosted: number
}

export interface SavingsMonth {
  label: string
  revenus: number
  depenses_reelles: number
  epargne_flow: number
}

export interface ReturnItem {
  type: string
  balance: number
  rate_pct: number
  source: "observed" | "manual" | "none"
}

export const TYPE_LABELS: Record<string, string> = {
  investissement: "Comptes d'investissement",
  investissement_non_mesure: "Investissements sans rendement mesuré",
  autres: "Courant et épargne",
}

export interface Forecast {
  computed_monthly_savings: number
  observed_investment_return_pct: number | null
  savings_overridden: boolean
  savings_months: SavingsMonth[]
  return_breakdown: ReturnItem[]
  current_wealth: number
  avg_monthly_savings: number
  months_used: number
  annual_return_pct: number
  years: number
  extra_monthly: number
  final_base: number
  final_boosted: number
  gain_from_extra: number
  points: ForecastPoint[]
}
