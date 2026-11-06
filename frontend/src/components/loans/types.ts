import i18n from "i18next"
import { appLocale } from "@/i18n/locale"
export type LoanKind = "immobilier" | "auto" | "consommation" | "etudiant" | "autre"
export type PrepaymentMode = "reduce_duration" | "reduce_payment"

export interface Prepayment {
  id: number
  date: string
  amount: number
  mode: PrepaymentMode
}

export interface LoanSummary {
  id: number
  account_id: number
  name: string
  institution: string | null
  logo: string | null
  color: string | null
  kind: LoanKind
  principal: number
  annual_rate_pct: number
  duration_months: number
  start_date: string
  insurance_monthly: number
  monthly_payment: number
  remaining_principal: number
  repaid_pct: number
  end_date: string
  total_interest: number
  total_insurance: number
  total_cost: number
  prepayments: Prepayment[]
}

export interface ScheduleRow {
  n: number
  date: string
  payment: number
  interest: number
  principal: number
  insurance: number
  remaining: number
  prepayment: number
}

export interface SimulationResult {
  interest_saved: number
  total_interest_before: number
  total_interest_after: number
  new_end_date: string
  months_saved: number
  new_payment: number
  max_penalty: number
}

export const loanKindLabel = (kind: LoanKind): string => i18n.t(`kind.${kind}`, { ns: "loans" })

export const PREPAYMENT_MODES: PrepaymentMode[] = ["reduce_duration", "reduce_payment"]
export const prepaymentModeLabel = (mode: PrepaymentMode): string => i18n.t(`prepayment.${mode}`, { ns: "loans" })

export function formatMonths(months: number): string {
  const years = Math.floor(months / 12)
  const rest = months % 12
  const monthsLabel = (n: number) => i18n.t("duration.months", { ns: "loans", count: n })
  if (!years) return monthsLabel(rest)
  const yearsLabel = i18n.t("duration.years", { ns: "loans", count: years })
  return rest ? i18n.t("duration.yearsAndMonths", { ns: "loans", years: yearsLabel, months: monthsLabel(rest) }) : yearsLabel
}

export function formatDateFr(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(appLocale(), { day: "numeric", month: "long", year: "numeric" })
}
