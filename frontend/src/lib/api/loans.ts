/** Crédits : échéancier, simulation et remboursements anticipés. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** PATCH /loans/:id */
export const patchLoansById = <T = ApiResponse<"/loans/{loan_id}", "patch">>(id: Id, body?: ApiBody<"/loans/{loan_id}", "patch">) => api.patch<T>(`/loans/${id}`, body)

/** POST /loans */
export const postLoans = <T = ApiResponse<"/loans", "post">>(body?: ApiBody<"/loans", "post">) => api.post<T>(`/loans`, body)

/** GET /loans/:id/schedule */
export const getLoansSchedule = <T = ApiResponse<"/loans/{loan_id}/schedule", "get">>(id: Id) => api.get<T>(`/loans/${id}/schedule`)

/** POST /loans/:id/simulate-prepayment */
export const postLoansSimulatePrepayment = <T = ApiResponse<"/loans/{loan_id}/simulate-prepayment", "post">>(id: Id, body?: ApiBody<"/loans/{loan_id}/simulate-prepayment", "post">) => api.post<T>(`/loans/${id}/simulate-prepayment`, body)

/** POST /loans/:id/prepayments */
export const postLoansPrepayments = <T = ApiResponse<"/loans/{loan_id}/prepayments", "post">>(id: Id, body?: ApiBody<"/loans/{loan_id}/prepayments", "post">) => api.post<T>(`/loans/${id}/prepayments`, body)

/** DELETE /loans/:id/prepayments/:id */
export const deleteLoansPrepaymentsById = <T = void>(id1: Id, id2: Id) => api.delete<T>(`/loans/${id1}/prepayments/${id2}`)

/** DELETE /loans/:id */
export const deleteLoansById = <T = void>(id: Id) => api.delete<T>(`/loans/${id}`)
