/** Récurrences et salaire. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** GET /recurring-transactions/ */
export const getRecurringTransactions = <T = ApiResponse<"/recurring-transactions/", "get">>() => api.get<T>(`/recurring-transactions/`)

/** POST /recurring-transactions/ */
export const postRecurringTransactions = <T = ApiResponse<"/recurring-transactions/", "post">>(body?: ApiBody<"/recurring-transactions/", "post">) => api.post<T>(`/recurring-transactions/`, body)

/** POST /recurring-transactions/trigger */
export const postRecurringTransactionsTrigger = <T = ApiResponse<"/recurring-transactions/trigger", "post">>(body?: unknown) => api.post<T>(`/recurring-transactions/trigger`, body)

/** DELETE /recurring-transactions/:id */
export const deleteRecurringTransactionsById = <T = ApiResponse<"/recurring-transactions/{recurring_tx_id}", "delete">>(id: Id) => api.delete<T>(`/recurring-transactions/${id}`)

/** PATCH /recurring-transactions/:id */
export const patchRecurringTransactionsById = <T = ApiResponse<"/recurring-transactions/{recurring_tx_id}", "patch">>(id: Id, body: ApiBody<"/recurring-transactions/{recurring_tx_id}", "patch">) => api.patch<T>(`/recurring-transactions/${id}`, body)

/** GET /salary/config */
export const getSalaryConfig = <T = ApiResponse<"/salary/config", "get">>() => api.get<T>(`/salary/config`)

/** POST /salary/config */
export const postSalaryConfig = <T = ApiResponse<"/salary/config", "post">>(body?: ApiBody<"/salary/config", "post">) => api.post<T>(`/salary/config`, body)

/** PUT /salary/config */
export const putSalaryConfig = <T = ApiResponse<"/salary/config", "put">>(body: ApiBody<"/salary/config", "put">) => api.put<T>(`/salary/config`, body)

/** DELETE /salary/generate/:id/:id */
export const deleteSalaryGenerateById = <T = ApiResponse<"/salary/generate/{year}/{month}", "delete">>(id1: Id, id2: Id) => api.delete<T>(`/salary/generate/${id1}/${id2}`)

/** POST /salary/generate/:id/:id */
export const postSalaryGenerateById = <T = ApiResponse<"/salary/generate/{year}/{month}", "post">>(id1: Id, id2: Id, body?: unknown) => api.post<T>(`/salary/generate/${id1}/${id2}`, body)

/** PUT /salary/months/:id/:id */
export const putSalaryMonthsById = <T = ApiResponse<"/salary/months/{year}/{month}", "put">>(id1: Id, id2: Id, body: ApiBody<"/salary/months/{year}/{month}", "put">) => api.put<T>(`/salary/months/${id1}/${id2}`, body)

/** GET /salary/summary/:id/:id */
export const getSalarySummaryById = <T = ApiResponse<"/salary/summary/{year}/{month}", "get">>(id1: Id, id2: Id) => api.get<T>(`/salary/summary/${id1}/${id2}`)

/** GET /salary/telecommuting/:id/:id */
export const getSalaryTelecommutingById = <T = ApiResponse<"/salary/telecommuting/{year}/{month}", "get">>(id1: Id, id2: Id) => api.get<T>(`/salary/telecommuting/${id1}/${id2}`)

/** PUT /salary/telecommuting/:id/:id */
export const putSalaryTelecommutingById = <T = ApiResponse<"/salary/telecommuting/{year}/{month}", "put">>(id1: Id, id2: Id, body: ApiBody<"/salary/telecommuting/{year}/{month}", "put">) => api.put<T>(`/salary/telecommuting/${id1}/${id2}`, body)

/** PATCH /benefits/:id */
export const patchBenefitsById = <T = ApiResponse<"/benefits/{benefit_id}", "patch">>(id: Id, body?: ApiBody<"/benefits/{benefit_id}", "patch">) => api.patch<T>(`/benefits/${id}`, body)

/** POST /benefits */
export const postBenefits = <T = ApiResponse<"/benefits", "post">>(body?: ApiBody<"/benefits", "post">) => api.post<T>(`/benefits`, body)

/** GET /benefits */
export const getBenefits = <T = ApiResponse<"/benefits", "get">>() => api.get<T>(`/benefits`)

/** GET /benefits/summary */
export const getBenefitsSummary = <T = ApiResponse<"/benefits/summary", "get">>() => api.get<T>(`/benefits/summary`)

/** DELETE /benefits/:id */
export const deleteBenefitsById = <T = void>(id: Id) => api.delete<T>(`/benefits/${id}`)

/** POST /benefits/:id/declared */
export const postBenefitsDeclared = <T = ApiResponse<"/benefits/{benefit_id}/declared", "post">>(id: Id, body?: ApiBody<"/benefits/{benefit_id}/declared", "post">) => api.post<T>(`/benefits/${id}/declared`, body)

/** PATCH /salary/work-time */
export const patchSalaryWorkTime = <T = ApiResponse<"/salary/work-time", "patch">>(body?: ApiBody<"/salary/work-time", "patch">) => api.patch<T>(`/salary/work-time`, body)

/** GET /salary/work-time */
export const getSalaryWorkTime = <T = ApiResponse<"/salary/work-time", "get">>() => api.get<T>(`/salary/work-time`)
