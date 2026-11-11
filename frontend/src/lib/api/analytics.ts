/** Lectures analytiques (KPI calculés par le backend). Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** GET /analytics/account-flow-summary */
export const getAnalyticsAccountFlowSummary = <T = ApiResponse<"/analytics/account-flow-summary", "get">>(query = "") => api.get<T>(`/analytics/account-flow-summary${query}`)

/** GET /analytics/actions */
export const getAnalyticsActions = <T = ApiResponse<"/analytics/actions", "get">>() => api.get<T>(`/analytics/actions`)

/** POST /analytics/actions/dismiss */
export const postAnalyticsActionsDismiss = <T = ApiResponse<"/analytics/actions/dismiss", "post">>(body?: ApiBody<"/analytics/actions/dismiss", "post">) => api.post<T>(`/analytics/actions/dismiss`, body)

/** GET /analytics/asset-allocation/suggestions */
export const getAnalyticsAssetAllocationSuggestions = <T = ApiResponse<"/analytics/asset-allocation/suggestions", "get">>() => api.get<T>(`/analytics/asset-allocation/suggestions`)

/** GET /analytics/audit/:id */
export const getAnalyticsAuditById = <T = ApiResponse<"/analytics/audit/{issue_id}", "get">>(id: Id) => api.get<T>(`/analytics/audit/${id}`)

/** GET /analytics/budget */
export const getAnalyticsBudget = <T = ApiResponse<"/analytics/budget", "get">>(query = "") => api.get<T>(`/analytics/budget${query}`)

/** GET /analytics/calendar */
export const getAnalyticsCalendar = <T = ApiResponse<"/analytics/calendar", "get">>(query = "") => api.get<T>(`/analytics/calendar${query}`)

/** GET /analytics/cashflow-projection */
export const getAnalyticsCashflowProjection = <T = ApiResponse<"/analytics/cashflow-projection", "get">>(query = "") => api.get<T>(`/analytics/cashflow-projection${query}`)

/** GET /analytics/diversity-scanner */
export const getAnalyticsDiversityScanner = <T = ApiResponse<"/analytics/diversity-scanner", "get">>() => api.get<T>(`/analytics/diversity-scanner`)

/** GET /analytics/investments-allocation */
export const getAnalyticsInvestmentsAllocation = <T = ApiResponse<"/analytics/investments-allocation", "get">>() => api.get<T>(`/analytics/investments-allocation`)

/** GET /analytics/investments-allocation-advanced */
export const getAnalyticsInvestmentsAllocationAdvanced = <T = ApiResponse<"/analytics/investments-allocation-advanced", "get">>() => api.get<T>(`/analytics/investments-allocation-advanced`)

/** GET /analytics/investments/:id */
export const getAnalyticsInvestmentsById = <T = ApiResponse<"/analytics/investments/{account_id}", "get">>(id: Id) => api.get<T>(`/analytics/investments/${id}`)

/** GET /analytics/investments/:id/performance-history */
export const getAnalyticsInvestmentsPerformanceHistory = <T = ApiResponse<"/analytics/investments/{account_id}/performance-history", "get">>(id: Id) => api.get<T>(`/analytics/investments/${id}/performance-history`)

/** GET /analytics/kpi-history */
export const getAnalyticsKpiHistory = <T = ApiResponse<"/analytics/kpi-history", "get">>(query = "") => api.get<T>(`/analytics/kpi-history${query}`)

/** GET /analytics/resilience */
export const getAnalyticsResilience = <T = ApiResponse<"/analytics/resilience", "get">>(query = "") => api.get<T>(`/analytics/resilience${query}`)

/** GET /analytics/subscriptions */
export const getAnalyticsSubscriptions = <T = ApiResponse<"/analytics/subscriptions", "get">>(query = "") => api.get<T>(`/analytics/subscriptions${query}`)

/** POST /analytics/subscriptions/ignore */
export const postAnalyticsSubscriptionsIgnore = <T = ApiResponse<"/analytics/subscriptions/ignore", "post">>(body?: ApiBody<"/analytics/subscriptions/ignore", "post">) => api.post<T>(`/analytics/subscriptions/ignore`, body)

/** GET /analytics/tags */
export const getAnalyticsTags = <T = ApiResponse<"/analytics/tags", "get">>(query = "") => api.get<T>(`/analytics/tags${query}`)

/** GET /analytics/timeseries */
export const getAnalyticsTimeseries = <T = ApiResponse<"/analytics/timeseries", "get">>(query = "") => api.get<T>(`/analytics/timeseries${query}`)

/** GET /analytics/wealth-forecast */
export const getAnalyticsWealthForecast = <T = ApiResponse<"/analytics/wealth-forecast", "get">>(query = "") => api.get<T>(`/analytics/wealth-forecast${query}`)

/** GET /analytics/wealth-simulation */
export const getAnalyticsWealthSimulation = <T = ApiResponse<"/analytics/wealth-simulation", "get">>(query = "") => api.get<T>(`/analytics/wealth-simulation${query}`)
