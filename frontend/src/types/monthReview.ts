export interface ReviewTransaction {
  id: number
  date: string
  merchant: string
  amount: number
  category_name: string | null
  is_exceptional: boolean
}

export interface ReviewAccount {
  id: number
  name: string
  currency: string
  balance: number
  last_verified_at: string
  verified_since_month_end: boolean
}

export interface BudgetAlertLite {
  category_id: number
  category_name: string
  monthly_limit: number | null
  monthly_spent: number
  monthly_ratio: number | null
}

export interface ReviewBudget {
  income: number
  real_expenses: number
  savings: number
  savings_rate: number
  burn_rate: number
  exceptional_expenses: number
  real_expenses_excl_exceptional: number
  savings_excl_exceptional: number
  savings_rate_excl_exceptional: number
  burn_rate_excl_exceptional: number
  previous_real_expenses: number
  alerts: BudgetAlertLite[]
  top_expenses: ReviewTransaction[]
}

export interface MonthClosureSummary {
  year: number
  month: number
  closed_at: string
  highlight: string | null
  tx_count: number
  income: number
  expenses: number
  unresolved_count: number
}

export interface MonthReview {
  year: number
  month: number
  closed: boolean
  closure: MonthClosureSummary | null
  modified_since_close: boolean
  categorize: { count: number; total: number; items: ReviewTransaction[] }
  accounts: { unverified_count: number; accounts: ReviewAccount[] }
  budget: ReviewBudget
}
