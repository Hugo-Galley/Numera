/** Comptes, relevés de solde (snapshots, point zéro) et crédits. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** GET /accounts */
export const getAccounts = <T = ApiResponse<"/accounts", "get">>() => api.get<T>(`/accounts`)

/** POST /accounts */
export const postAccounts = <T = ApiResponse<"/accounts", "post">>(body?: ApiBody<"/accounts", "post">) => api.post<T>(`/accounts`, body)

/** DELETE /accounts/:id */
export const deleteAccountsById = <T = any>(id: Id) => api.delete<T>(`/accounts/${id}`)

/** GET /accounts/:id */
export const getAccountsById = <T = any>(id: Id) => api.get<T>(`/accounts/${id}`)

/** PATCH /accounts/:id */
export const patchAccountsById = <T = any>(id: Id, body: any) => api.patch<T>(`/accounts/${id}`, body)

/** POST /balance-snapshots */
export const postBalanceSnapshots = <T = any>(body?: any) => api.post<T>(`/balance-snapshots`, body)

/** POST /balance-snapshots/set-zero-point */
export const postBalanceSnapshotsSetZeroPoint = <T = any>(body?: any) => api.post<T>(`/balance-snapshots/set-zero-point`, body)

/** DELETE /balance-snapshots/:id */
export const deleteBalanceSnapshotsById = <T = any>(id: Id) => api.delete<T>(`/balance-snapshots/${id}`)

/** PATCH /balance-snapshots/:id */
export const patchBalanceSnapshotsById = <T = any>(id: Id, body: any) => api.patch<T>(`/balance-snapshots/${id}`, body)

/** GET /loans/by-account/:id */
export const getLoansByAccountById = <T = any>(id: Id) => api.get<T>(`/loans/by-account/${id}`)
