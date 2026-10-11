export interface ExpenseRef {
  id: number
  account_id: number
  date: string
  label: string
  amount: number
}

export interface ClaimAllocation {
  id: number
  entree_id: number
  amount: number
  date: string | null
  label: string | null
  account_id: number | null
}

export interface Claim {
  id: number
  debtor: string
  expected_amount: number
  received: number
  remaining: number
  note: string | null
  created_at: string
  currency: string
  expense: ExpenseRef
  allocations: ClaimAllocation[]
}

export interface DebtorDue {
  debtor: string
  claims: number
  due: number
}

export interface ReimbursementSummary {
  total_due: number
  debtors: DebtorDue[]
}

export interface ClaimCandidate {
  id: number
  account_id: number
  date: string
  label: string
  amount: number
  available: number
  day_gap: number
  debtor_match: boolean
}

export interface EntryClaims {
  entree_id: number
  amount: number
  available: number
  open_claims: Claim[]
  allocations: { id: number; claim_id: number; amount: number; debtor: string }[]
}

export interface ReimbursableTransaction {
  id: number
  type: string
  merchant: string
  date: string
  amount: number
  currency: string
}
