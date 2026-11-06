import i18n from "i18next"



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

/** Libellés d'affichage des groupes de comptes (évalués à la lecture : la langue peut changer). */
export const TYPE_LABELS: Record<string, string> = {
  get investissement() { return i18n.t("misc.typeInvest", { ns: "tools" }) },
  get investissement_non_mesure() { return i18n.t("misc.typeInvestUnmeasured", { ns: "tools" }) },
  get autres() { return i18n.t("misc.typeOther", { ns: "tools" }) },
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
