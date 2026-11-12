import { monthShort } from "@/i18n/locale"
import type { ApiBody } from "@/lib/api/types"


/** Mois (1 à 12) avec leur libellé abrégé dans la langue courante (lu à l'accès : pas figé à l'import). */
export const MONTHS = Array.from({ length: 12 }, (_, i) => ({
  value: i + 1,
  get label() {
    const label = monthShort(i + 1).replace(/\.$/, "")
    return label.charAt(0).toUpperCase() + label.slice(1)
  },
}))
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
  security_name?: string | null
  quantity?: number | null
  unit_price?: number | null
  whole_shares?: boolean
  etf_profile_id?: number | null
  logo?: string | null
  category?: Category
}

type RecurringBody = ApiBody<"/recurring-transactions/", "post">

/** Fréquence et type acceptés par l'API des récurrences (le formulaire les garde en `string`). */
export type RecurringFrequency = RecurringBody["frequency"]
export type RecurringType = RecurringBody["type"]
