export interface WrappedMonth {
  month: number
  income: number
  real_expenses: number
  saved: number
}

export interface WrappedCategory {
  name: string
  icon: string | null
  color: string | null
  total: number
  percentage: number
  work_hours: number | null
}

export interface WrappedMerchant {
  merchant: string
  total: number
  work_hours: number | null
}

export interface WrappedExpense {
  merchant: string
  amount: number
  date: string
  category: string | null
  work_hours: number | null
}

export interface WrappedSubscription {
  name: string
  monthly_cost: number
}

export interface WrappedTotals {
  income: number
  real_expenses: number
  saved: number
  savings_rate: number
  invested: number
  dividends: number
  net_worth_start: number
  net_worth_end: number
  net_worth_change: number
  subscriptions_cost: number
  expense_count: number
}

export interface WrappedComparison {
  year: number
  totals: WrappedTotals
  income_change_pct: number | null
  real_expenses_change_pct: number | null
  savings_rate_change_pts: number
  net_worth_change_diff: number
  invested_change_pct: number | null
}

export interface WrappedReport {
  year: number
  available_years: number[]
  has_data: boolean
  is_partial: boolean
  months_covered: number
  totals: WrappedTotals
  months: WrappedMonth[]
  most_expensive_month: WrappedMonth | null
  thriftiest_month: WrappedMonth | null
  top_categories: WrappedCategory[]
  top_merchants: WrappedMerchant[]
  biggest_expense: WrappedExpense | null
  hourly_rate: number | null
  real_expenses_work_hours: number | null
  net_worth_change_pct: number | null
  new_subscriptions: WrappedSubscription[]
  stopped_subscriptions: WrappedSubscription[]
  stopped_subscriptions_yearly_saving: number
  previous: WrappedComparison | null
}
