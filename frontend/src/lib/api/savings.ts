/** Objectifs d'épargne et provisions. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** GET /goals */
export const getGoals = <T = ApiResponse<"/goals", "get">>() => api.get<T>(`/goals`)

/** POST /goals */
export const postGoals = <T = ApiResponse<"/goals", "post">>(body?: ApiBody<"/goals", "post">) => api.post<T>(`/goals`, body)

/** DELETE /goals/:id */
export const deleteGoalsById = <T = ApiResponse<"/goals/{goal_id}", "delete">>(id: Id) => api.delete<T>(`/goals/${id}`)

/** PATCH /goals/:id */
export const patchGoalsById = <T = ApiResponse<"/goals/{goal_id}", "patch">>(id: Id, body: ApiBody<"/goals/{goal_id}", "patch">) => api.patch<T>(`/goals/${id}`, body)

/** GET /provisions */
export const getProvisions = <T = ApiResponse<"/provisions", "get">>() => api.get<T>(`/provisions`)

/** POST /provisions */
export const postProvisions = <T = ApiResponse<"/provisions", "post">>(body?: ApiBody<"/provisions", "post">) => api.post<T>(`/provisions`, body)

/** GET /provisions/summary */
export const getProvisionsSummary = <T = ApiResponse<"/provisions/summary", "get">>() => api.get<T>(`/provisions/summary`)

/** DELETE /provisions/:id */
export const deleteProvisionsById = <T = void>(id: Id) => api.delete<T>(`/provisions/${id}`)

/** PATCH /provisions/:id */
export const patchProvisionsById = <T = ApiResponse<"/provisions/{provision_id}", "patch">>(id: Id, body: ApiBody<"/provisions/{provision_id}", "patch">) => api.patch<T>(`/provisions/${id}`, body)
