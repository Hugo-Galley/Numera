/** Lectures analytiques (KPI calculés par le backend). Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { Id } from "./types"

/** GET /analytics/account-flow-summary */
export const getAnalyticsAccountFlowSummary = <T = any>(query = "") => api.get<T>(`/analytics/account-flow-summary${query}`)

/** GET /analytics/actions */
export const getAnalyticsActions = <T = any>() => api.get<T>(`/analytics/actions`)

/** POST /analytics/actions/dismiss */
export const postAnalyticsActionsDismiss = <T = any>(body?: any) => api.post<T>(`/analytics/actions/dismiss`, body)

/** GET /analytics/asset-allocation/suggestions */
export const getAnalyticsAssetAllocationSuggestions = <T = any>() => api.get<T>(`/analytics/asset-allocation/suggestions`)

/** GET /analytics/audit/:id */
export const getAnalyticsAuditById = <T = any>(id: Id) => api.get<T>(`/analytics/audit/${id}`)

/** GET /analytics/budget */
export const getAnalyticsBudget = <T = any>(query = "") => api.get<T>(`/analytics/budget${query}`)

/** GET /analytics/calendar */
export const getAnalyticsCalendar = <T = any>(query = "") => api.get<T>(`/analytics/calendar${query}`)

/** GET /analytics/diversity-scanner */
export const getAnalyticsDiversityScanner = <T = any>() => api.get<T>(`/analytics/diversity-scanner`)

/** GET /analytics/investments-allocation */
export const getAnalyticsInvestmentsAllocation = <T = any>() => api.get<T>(`/analytics/investments-allocation`)

/** GET /analytics/investments-allocation-advanced */
export const getAnalyticsInvestmentsAllocationAdvanced = <T = any>() => api.get<T>(`/analytics/investments-allocation-advanced`)

/** GET /analytics/investments/:id */
export const getAnalyticsInvestmentsById = <T = any>(id: Id) => api.get<T>(`/analytics/investments/${id}`)

/** GET /analytics/investments/:id/performance-history */
export const getAnalyticsInvestmentsPerformanceHistory = <T = any>(id: Id) => api.get<T>(`/analytics/investments/${id}/performance-history`)

/** GET /analytics/kpi-history */
export const getAnalyticsKpiHistory = <T = any>(query = "") => api.get<T>(`/analytics/kpi-history${query}`)

/** GET /analytics/resilience */
export const getAnalyticsResilience = <T = any>(query = "") => api.get<T>(`/analytics/resilience${query}`)

/** GET /analytics/subscriptions */
export const getAnalyticsSubscriptions = <T = any>(query = "") => api.get<T>(`/analytics/subscriptions${query}`)

/** POST /analytics/subscriptions/ignore */
export const postAnalyticsSubscriptionsIgnore = <T = any>(body?: any) => api.post<T>(`/analytics/subscriptions/ignore`, body)

/** GET /analytics/tags */
export const getAnalyticsTags = <T = any>(query = "") => api.get<T>(`/analytics/tags${query}`)

/** GET /analytics/timeseries */
export const getAnalyticsTimeseries = <T = any>(query = "") => api.get<T>(`/analytics/timeseries${query}`)

/** GET /analytics/wealth-forecast */
export const getAnalyticsWealthForecast = <T = any>(query = "") => api.get<T>(`/analytics/wealth-forecast${query}`)

/** GET /analytics/wealth-simulation */
export const getAnalyticsWealthSimulation = <T = any>(query = "") => api.get<T>(`/analytics/wealth-simulation${query}`)
