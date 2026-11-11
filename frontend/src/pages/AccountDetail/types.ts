import { type SplitPart } from "@/components/transactions/SplitTransactionDialog"

export type Account = {
  balance?: number
  id: number
  name: string
  logo?: string | null
  type: "courant" | "epargne" | "investissement" | "assurance_vie" | "credit"
  currency: string
  fonds_euros_pct?: number
  fonds_investis_pct?: number
  valuation_mode?: "positions" | "snapshot"
  last_verified_at?: string
}

export type Category = {
  id: number
  name: string
  type?: string
  icon?: string
  color?: string
  archived?: boolean
}

export type TagType = {
  id: number
  name: string
  color: string | null
  archived?: boolean
}

export type Transaction = {
  id: number
  account_id: number
  date: string
  type: string
  merchant: string
  recurring_logo?: string | null
  merchant_id: number | null
  merchant_obj?: {
    id: number
    name: string
    color: string | null
  } | null
  amount: number
  currency: string
  original_amount: number
  running_balance: number
  category_id: number | null
  category: Category | null
  tags: TagType[]
  note: string | null
  is_recurring: boolean
  custom_icon: string | null
  custom_color: string | null
  is_transfer?: boolean
  is_exceptional?: boolean
  reimbursement_offset?: number
  reimbursement_expected?: number
  /** Saisie datée après aujourd'hui : ne compte dans aucun solde ni total avant sa date (calculé par le backend). */
  is_upcoming?: boolean
  has_claims?: boolean
  splits?: (SplitPart & { category?: Category | null })[]
}

// Taille d'une page de transactions (l'API renvoie 100 lignes par défaut, 1000 au plus)
export const TX_PAGE_SIZE = 200
