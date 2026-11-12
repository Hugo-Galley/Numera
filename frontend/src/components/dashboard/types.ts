/** Données du tableau de bord : types du contrat de l'API (`/analytics/*`), pour que `tsc` suive le backend. */
import type { ApiResponse } from "@/lib/api/types"

export type DashboardAccount = ApiResponse<"/accounts", "get">[number]
export type BudgetOverview = ApiResponse<"/analytics/budget", "get">
export type ExpensesByCategory = ApiResponse<"/analytics/expenses-by-category", "get">
export type KpiHistoryPoint = ApiResponse<"/analytics/kpi-history", "get">[number]
export type TopMerchants = ApiResponse<"/analytics/top-merchants", "get">
export type SubscriptionsData = ApiResponse<"/analytics/subscriptions", "get">
export type Timeseries = ApiResponse<"/analytics/timeseries", "get">
export type PatrimoineAllocation = ApiResponse<"/analytics/patrimoine-allocation", "get">
export type BudgetAlert = ApiResponse<"/analytics/budget-alerts", "get">[number]
export type Insights = ApiResponse<"/analytics/insights", "get">
export type SankeyData = ApiResponse<"/analytics/sankey", "get">
export type CashflowProjection = ApiResponse<"/analytics/cashflow-projection", "get">
export type TagSpending = ApiResponse<"/analytics/tags", "get">[number]
