import type { ApiBody, ApiResponse } from "@/lib/api/types"


export const GOAL_COLORS = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#f43f5e", "#06b6d4", "#ec4899", "#64748b"]

export interface Resilience {
  months: number | null
  liquid_savings: number
  avg_monthly_real_expenses: number
  months_used: number
}

/** Types du contrat de l'API pour la page Épargne. */
export type SavingsAnalytics = ApiResponse<"/analytics/budget", "get">
export type KpiPoint = ApiResponse<"/analytics/kpi-history", "get">[number]
export type Goal = ApiResponse<"/goals", "get">[number]
export type GoalBody = ApiBody<"/goals", "post">
export type SavingsAccount = ApiResponse<"/accounts", "get">[number]
export type SavingsCategory = ApiResponse<"/categories", "get">[number]
