export interface AccountLite {
  id: number
  name: string
  type: string
  currency: string
}

export interface TransferRule {
  id: number
  source_account_id: number
  dest_account_id: number
  pattern: string | null
  amount: number | null
  amount_tolerance_pct: number
  day_tolerance: number
  is_active: boolean
}

export interface TransferLeg {
  id: number
  account_id: number
  date: string
  amount: number
  currency: string
  label: string | null
}

export interface TransferPairPreview {
  rule_id: number | null
  kind: "regular" | "investment"
  day_gap: number
  sortie: TransferLeg
  entree: TransferLeg
}

export interface TransferApplyResult {
  dry_run: boolean
  count: number
  pairs: TransferPairPreview[]
}

export interface TransferCandidate {
  sortie_id: number
  other_id: number
  type: "regular" | "investment"
  account_id: number
  date: string
  amount: number
  currency: string
  label: string | null
  day_gap: number
  amount_gap_pct: number
}

export interface PotentialTransfer {
  sortie: { id: number; account_id: number; merchant: string; date: string; amount: number; currency: string }
  entree: { id: number; account_id: number; merchant?: string; note?: string | null; date: string; amount: number; currency: string }
  type: "regular" | "investment"
  confidence: "high" | "medium"
  ambiguous: boolean
  day_gap: number
}

export interface LinkedTransfer {
  id: number
  account_id: number
  merchant: string
  date: string
  amount: number
  currency: string
  type: string
  link_origin: "manual" | "rule" | "recurring" | null
  linked_account_id: number | null
}
