/** Transactions et import de relevés. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { Id } from "./types"

/** POST (multipart) /import/commit */
export const uploadImportCommit = <T = any>(formData: FormData) => api.upload<T>(`/import/commit`, formData)

/** POST (multipart) /import/preview */
export const uploadImportPreview = <T = any>(formData: FormData) => api.upload<T>(`/import/preview`, formData)

/** GET /transactions */
export const getTransactions = <T = any>(query = "") => api.get<T>(`/transactions${query}`)

/** POST /transactions */
export const postTransactions = <T = any>(body?: any) => api.post<T>(`/transactions`, body)

/** PATCH /transactions/bulk */
export const patchTransactionsBulk = <T = any>(body: any) => api.patch<T>(`/transactions/bulk`, body)

/** POST /transactions/bulk-delete */
export const postTransactionsBulkDelete = <T = any>(body?: any) => api.post<T>(`/transactions/bulk-delete`, body)

/** GET /transactions/merchants */
export const getTransactionsMerchants = <T = any>() => api.get<T>(`/transactions/merchants`)

/** DELETE /transactions/:id */
export const deleteTransactionsById = <T = any>(id: Id) => api.delete<T>(`/transactions/${id}`)

/** PATCH /transactions/:id */
export const patchTransactionsById = <T = any>(id: Id, body: any) => api.patch<T>(`/transactions/${id}`, body)

/** POST /transactions/:id/ignore */
export const postTransactionsIgnore = <T = any>(id: Id, body?: any) => api.post<T>(`/transactions/${id}/ignore`, body)

/** POST /transactions/:id/ignore-duplicate */
export const postTransactionsIgnoreDuplicate = <T = any>(id: Id, body?: any) => api.post<T>(`/transactions/${id}/ignore-duplicate`, body)

/** POST /transactions/:id/link/:id */
export const postTransactionsLinkById = <T = any>(id1: Id, id2: Id, query = "", body?: any) => api.post<T>(`/transactions/${id1}/link/${id2}${query}`, body)
