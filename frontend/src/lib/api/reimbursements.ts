/** Remboursements : créances sur une dépense et affectation d'entrées. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** GET /reimbursements/claims/:id/candidates */
export const getReimbursementsClaimsCandidates = <T = ApiResponse<"/reimbursements/claims/{claim_id}/candidates", "get">>(id: Id) => api.get<T>(`/reimbursements/claims/${id}/candidates`)

/** POST /reimbursements/claims/:id/allocations */
export const postReimbursementsClaimsAllocations = <T = ApiResponse<"/reimbursements/claims/{claim_id}/allocations", "post">>(id: Id, body?: ApiBody<"/reimbursements/claims/{claim_id}/allocations", "post">) => api.post<T>(`/reimbursements/claims/${id}/allocations`, body)

/** GET /reimbursements/claims */
export const getReimbursementsClaims = <T = ApiResponse<"/reimbursements/claims", "get">>(query = "") => api.get<T>(`/reimbursements/claims${query}`)

/** GET /reimbursements/entries/:id/claims */
export const getReimbursementsEntriesClaims = <T = ApiResponse<"/reimbursements/entries/{entree_id}/claims", "get">>(id: Id) => api.get<T>(`/reimbursements/entries/${id}/claims`)

/** POST /reimbursements/claims */
export const postReimbursementsClaims = <T = ApiResponse<"/reimbursements/claims", "post">>(body?: ApiBody<"/reimbursements/claims", "post">) => api.post<T>(`/reimbursements/claims`, body)

/** DELETE /reimbursements/claims/:id */
export const deleteReimbursementsClaimsById = <T = void>(id: Id) => api.delete<T>(`/reimbursements/claims/${id}`)

/** PATCH /reimbursements/claims/:id */
export const patchReimbursementsClaimsById = <T = ApiResponse<"/reimbursements/claims/{claim_id}", "patch">>(id: Id, body?: ApiBody<"/reimbursements/claims/{claim_id}", "patch">) => api.patch<T>(`/reimbursements/claims/${id}`, body)

/** DELETE /reimbursements/allocations/:id */
export const deleteReimbursementsAllocationsById = <T = void>(id: Id) => api.delete<T>(`/reimbursements/allocations/${id}`)

/** GET /reimbursements/summary */
export const getReimbursementsSummary = <T = ApiResponse<"/reimbursements/summary", "get">>() => api.get<T>(`/reimbursements/summary`)
