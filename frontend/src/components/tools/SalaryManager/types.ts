

export interface SalaryConfig {
  id?: number
  salary_account_id: number | ""
  ticket_account_id?: number | ""
  net_salary: number
  ticket_value: number
  ticket_employee_share: number
  salary_category_id: number | ""
  ticket_category_id?: number | ""
}

export interface Account {
  id: number
  name: string
  type: string
}

export interface Category {
  id: number
  name: string
}

export interface MonthSummary {
  net_salary: number
  tt_days_count: number
  ticket_deduction: number
  real_salary: number
  ticket_credit: number
}
