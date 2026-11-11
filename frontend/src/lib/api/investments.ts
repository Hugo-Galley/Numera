/** Positions, opérations d'investissement, profils ETF, marché et fiscalité. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** POST /etf-profiles/auto-decompose */
export const postEtfProfilesAutoDecompose = <T = ApiResponse<"/etf-profiles/auto-decompose", "post">>(body?: ApiBody<"/etf-profiles/auto-decompose", "post">) => api.post<T>(`/etf-profiles/auto-decompose`, body)

/** POST /etf-profiles/refresh-held */
export const postEtfProfilesRefreshHeld = <T = ApiResponse<"/etf-profiles/refresh-held", "post">>(body?: unknown) => api.post<T>(`/etf-profiles/refresh-held`, body)

/** GET /holdings */
export const getHoldings = <T = ApiResponse<"/holdings", "get">>(query = "") => api.get<T>(`/holdings${query}`)

/** POST /holdings/baseline */
export const postHoldingsBaseline = <T = ApiResponse<"/holdings/baseline", "post">>(body?: ApiBody<"/holdings/baseline", "post">) => api.post<T>(`/holdings/baseline`, body)

/** GET /holdings/suggestions */
export const getHoldingsSuggestions = <T = ApiResponse<"/holdings/suggestions", "get">>(query = "") => api.get<T>(`/holdings/suggestions${query}`)

/** DELETE /holdings/:id */
export const deleteHoldingsById = <T = void>(id: Id) => api.delete<T>(`/holdings/${id}`)

/** PUT /holdings/:id */
export const putHoldingsById = <T = ApiResponse<"/holdings/{holding_id}", "put">>(id: Id, body: ApiBody<"/holdings/{holding_id}", "put">) => api.put<T>(`/holdings/${id}`, body)

/** POST /investment-transactions */
export const postInvestmentTransactions = <T = ApiResponse<"/investment-transactions", "post">>(body?: ApiBody<"/investment-transactions", "post">) => api.post<T>(`/investment-transactions`, body)

/** DELETE /investment-transactions/:id */
export const deleteInvestmentTransactionsById = <T = void>(id: Id) => api.delete<T>(`/investment-transactions/${id}`)

/** PATCH /investment-transactions/:id */
export const patchInvestmentTransactionsById = <T = ApiResponse<"/investment-transactions/{transaction_id}", "patch">>(id: Id, body: ApiBody<"/investment-transactions/{transaction_id}", "patch">) => api.patch<T>(`/investment-transactions/${id}`, body)

/** GET /market/quote */
export const getMarketQuote = <T = ApiResponse<"/market/quote", "get">>(query = "") => api.get<T>(`/market/quote${query}`)

/** GET /market/search */
export const getMarketSearch = <T = ApiResponse<"/market/search", "get">>(query = "") => api.get<T>(`/market/search${query}`)

/** GET /tax/annual-report */
export const getTaxAnnualReport = <T = ApiResponse<"/tax/annual-report", "get">>(query = "") => api.get<T>(`/tax/annual-report${query}`)

/** GET /tax/overview */
export const getTaxOverview = <T = ApiResponse<"/tax/overview", "get">>() => api.get<T>(`/tax/overview`)

/** PATCH /tax/settings */
export const patchTaxSettings = <T = ApiResponse<"/tax/settings", "patch">>(body: ApiBody<"/tax/settings", "patch">) => api.patch<T>(`/tax/settings`, body)
