/** Transactions et import de relevés. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** POST (multipart) /import/commit */
export const uploadImportCommit = <T = ApiResponse<"/import/commit", "post">>(formData: FormData) => api.upload<T>(`/import/commit`, formData)

/** POST (multipart) /import/preview */
export const uploadImportPreview = <T = ApiResponse<"/import/preview", "post">>(formData: FormData) => api.upload<T>(`/import/preview`, formData)

/** GET /transactions */
export const getTransactions = <T = ApiResponse<"/transactions", "get">>(query = "") => api.get<T>(`/transactions${query}`)

/** POST /transactions */
export const postTransactions = <T = ApiResponse<"/transactions", "post">>(body?: ApiBody<"/transactions", "post">) => api.post<T>(`/transactions`, body)

/** PATCH /transactions/bulk */
export const patchTransactionsBulk = <T = void>(body: ApiBody<"/transactions/bulk", "patch">) => api.patch<T>(`/transactions/bulk`, body)

/** POST /transactions/bulk-delete */
export const postTransactionsBulkDelete = <T = ApiResponse<"/transactions/bulk-delete", "post">>(body?: ApiBody<"/transactions/bulk-delete", "post">) => api.post<T>(`/transactions/bulk-delete`, body)

/** GET /transactions/merchants */
export const getTransactionsMerchants = <T = ApiResponse<"/transactions/merchants", "get">>() => api.get<T>(`/transactions/merchants`)

/** DELETE /transactions/:id */
export const deleteTransactionsById = <T = void>(id: Id) => api.delete<T>(`/transactions/${id}`)

/** PATCH /transactions/:id */
export const patchTransactionsById = <T = ApiResponse<"/transactions/{transaction_id}", "patch">>(id: Id, body: ApiBody<"/transactions/{transaction_id}", "patch">) => api.patch<T>(`/transactions/${id}`, body)

/** POST /transactions/:id/ignore */
export const postTransactionsIgnore = <T = void>(id: Id, body?: unknown) => api.post<T>(`/transactions/${id}/ignore`, body)

/** POST /transactions/:id/ignore-duplicate */
export const postTransactionsIgnoreDuplicate = <T = void>(id: Id, body?: unknown) => api.post<T>(`/transactions/${id}/ignore-duplicate`, body)

/** POST /transactions/:id/link/:id */
export const postTransactionsLinkById = <T = ApiResponse<"/transactions/{transaction_id}/link/{other_id}", "post">>(id1: Id, id2: Id, query = "", body?: unknown) => api.post<T>(`/transactions/${id1}/link/${id2}${query}`, body)
