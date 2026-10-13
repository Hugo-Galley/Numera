export interface Insight {
  type: "anomaly" | "positive" | "advice"
  title: string
  description: string
  severity: "low" | "medium" | "high"
  value?: number
}

export interface FlowBlock {
  amount: number
  percentage: number
  diff_prev_month: number
  diff_prev_month_pct: number
}

export interface MoneyFlow {
  income: number
  fixed_charges: FlowBlock
  variable_expenses: FlowBlock
  savings: FlowBlock
  investments: FlowBlock
  remainder: FlowBlock
}

export interface ReportCategory {
  name: string
  total: number
  prev_total: number
  icon?: string
  color?: string
}

export interface MonthlyReportData {
  month: number
  year: number
  income: number
  real_expenses: number
  savings_rate: number
  net_worth_change: number
  top_categories: ReportCategory[]
  comparison: {
    income_diff: number
    income_diff_pct: number
    expenses_diff: number
    expenses_diff_pct: number
  }
  insights: Insight[]
  exceptional_expenses: number
  real_expenses_excl_exceptional: number
  savings_rate_excl_exceptional: number
  money_flow?: MoneyFlow
}

export interface BudgetLine {
  category_id: number
  category_name: string
  monthly_limit: number | null
  monthly_spent: number
  monthly_ratio: number | null
}

export interface ClosureLite {
  year: number
  month: number
  unresolved_count: number
}
