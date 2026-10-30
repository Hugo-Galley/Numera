/** Récurrences et salaire. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { Id } from "./types"

/** GET /recurring-transactions/ */
export const getRecurringTransactions = <T = any>() => api.get<T>(`/recurring-transactions/`)

/** POST /recurring-transactions/ */
export const postRecurringTransactions = <T = any>(body?: any) => api.post<T>(`/recurring-transactions/`, body)

/** POST /recurring-transactions/trigger */
export const postRecurringTransactionsTrigger = <T = any>(body?: any) => api.post<T>(`/recurring-transactions/trigger`, body)

/** DELETE /recurring-transactions/:id */
export const deleteRecurringTransactionsById = <T = any>(id: Id) => api.delete<T>(`/recurring-transactions/${id}`)

/** PATCH /recurring-transactions/:id */
export const patchRecurringTransactionsById = <T = any>(id: Id, body: any) => api.patch<T>(`/recurring-transactions/${id}`, body)

/** GET /salary/config */
export const getSalaryConfig = <T = any>() => api.get<T>(`/salary/config`)

/** POST /salary/config */
export const postSalaryConfig = <T = any>(body?: any) => api.post<T>(`/salary/config`, body)

/** PUT /salary/config */
export const putSalaryConfig = <T = any>(body: any) => api.put<T>(`/salary/config`, body)

/** DELETE /salary/generate/:id/:id */
export const deleteSalaryGenerateById = <T = any>(id1: Id, id2: Id) => api.delete<T>(`/salary/generate/${id1}/${id2}`)

/** POST /salary/generate/:id/:id */
export const postSalaryGenerateById = <T = any>(id1: Id, id2: Id, body?: any) => api.post<T>(`/salary/generate/${id1}/${id2}`, body)

/** PUT /salary/months/:id/:id */
export const putSalaryMonthsById = <T = any>(id1: Id, id2: Id, body: any) => api.put<T>(`/salary/months/${id1}/${id2}`, body)

/** GET /salary/summary/:id/:id */
export const getSalarySummaryById = <T = any>(id1: Id, id2: Id) => api.get<T>(`/salary/summary/${id1}/${id2}`)

/** GET /salary/telecommuting/:id/:id */
export const getSalaryTelecommutingById = <T = any>(id1: Id, id2: Id) => api.get<T>(`/salary/telecommuting/${id1}/${id2}`)

/** PUT /salary/telecommuting/:id/:id */
export const putSalaryTelecommutingById = <T = any>(id1: Id, id2: Id, body: any) => api.put<T>(`/salary/telecommuting/${id1}/${id2}`, body)
