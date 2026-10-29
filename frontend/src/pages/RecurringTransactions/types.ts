

export const MONTHS = [
  { value: 1, label: "Jan" },
  { value: 2, label: "Fév" },
  { value: 3, label: "Mar" },
  { value: 4, label: "Avr" },
  { value: 5, label: "Mai" },
  { value: 6, label: "Juin" },
  { value: 7, label: "Juil" },
  { value: 8, label: "Août" },
  { value: 9, label: "Sep" },
  { value: 10, label: "Oct" },
  { value: 11, label: "Nov" },
  { value: 12, label: "Déc" },
]
export type Category = {
  id: number
  name: string
  color: string
}

export type Account = {
  id: number
  name: string
  currency: string
  type: "courant" | "epargne" | "investissement"
  institution?: string | null
  logo?: string | null
}

export type RecurringTransaction = {
  id: number
  account_id: number
  name: string
  type: string
  amount: number
  currency: string
  category_id: number | null
  frequency: string
  day_of_month: number | null
  excluded_months?: number[] | null
  start_date: string
  end_date: string | null
  last_generated_date: string | null
  is_active: boolean
  auto_generate: boolean
  note: string | null
  transfer_to_account_id?: number | null
  transfer_credit_day?: number | null
  asset_class?: string | null
  sector?: string | null
  geographic_zone?: string | null
  ticker?: string | null
  isin?: string | null
  quantity?: number | null
  unit_price?: number | null
  whole_shares?: boolean
  etf_profile_id?: number | null
  logo?: string | null
  category?: Category
}
