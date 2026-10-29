/** Positions, opérations d'investissement, profils ETF, marché et fiscalité. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { Id } from "./types"

/** POST /etf-profiles/auto-decompose */
export const postEtfProfilesAutoDecompose = <T = any>(body?: any) => api.post<T>(`/etf-profiles/auto-decompose`, body)

/** POST /etf-profiles/refresh-held */
export const postEtfProfilesRefreshHeld = <T = any>(body?: any) => api.post<T>(`/etf-profiles/refresh-held`, body)

/** GET /holdings */
export const getHoldings = <T = any>(query = "") => api.get<T>(`/holdings${query}`)

/** POST /holdings/baseline */
export const postHoldingsBaseline = <T = any>(body?: any) => api.post<T>(`/holdings/baseline`, body)

/** GET /holdings/suggestions */
export const getHoldingsSuggestions = <T = any>(query = "") => api.get<T>(`/holdings/suggestions${query}`)

/** DELETE /holdings/:id */
export const deleteHoldingsById = <T = any>(id: Id) => api.delete<T>(`/holdings/${id}`)

/** PUT /holdings/:id */
export const putHoldingsById = <T = any>(id: Id, body: any) => api.put<T>(`/holdings/${id}`, body)

/** POST /investment-transactions */
export const postInvestmentTransactions = <T = any>(body?: any) => api.post<T>(`/investment-transactions`, body)

/** DELETE /investment-transactions/:id */
export const deleteInvestmentTransactionsById = <T = any>(id: Id) => api.delete<T>(`/investment-transactions/${id}`)

/** PATCH /investment-transactions/:id */
export const patchInvestmentTransactionsById = <T = any>(id: Id, body: any) => api.patch<T>(`/investment-transactions/${id}`, body)

/** GET /market/quote */
export const getMarketQuote = <T = any>(query = "") => api.get<T>(`/market/quote${query}`)

/** GET /market/search */
export const getMarketSearch = <T = any>(query = "") => api.get<T>(`/market/search${query}`)

/** GET /tax/annual-report */
export const getTaxAnnualReport = <T = any>(query = "") => api.get<T>(`/tax/annual-report${query}`)

/** GET /tax/overview */
export const getTaxOverview = <T = any>() => api.get<T>(`/tax/overview`)

/** PATCH /tax/settings */
export const patchTaxSettings = <T = any>(body: any) => api.patch<T>(`/tax/settings`, body)
