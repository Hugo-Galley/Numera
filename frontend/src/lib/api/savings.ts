/** Objectifs d'épargne et provisions. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { Id } from "./types"

/** GET /goals */
export const getGoals = <T = any>() => api.get<T>(`/goals`)

/** POST /goals */
export const postGoals = <T = any>(body?: any) => api.post<T>(`/goals`, body)

/** DELETE /goals/:id */
export const deleteGoalsById = <T = any>(id: Id) => api.delete<T>(`/goals/${id}`)

/** PATCH /goals/:id */
export const patchGoalsById = <T = any>(id: Id, body: any) => api.patch<T>(`/goals/${id}`, body)

/** GET /provisions */
export const getProvisions = <T = any>() => api.get<T>(`/provisions`)

/** POST /provisions */
export const postProvisions = <T = any>(body?: any) => api.post<T>(`/provisions`, body)

/** GET /provisions/summary */
export const getProvisionsSummary = <T = any>() => api.get<T>(`/provisions/summary`)

/** DELETE /provisions/:id */
export const deleteProvisionsById = <T = any>(id: Id) => api.delete<T>(`/provisions/${id}`)

/** PATCH /provisions/:id */
export const patchProvisionsById = <T = any>(id: Id, body: any) => api.patch<T>(`/provisions/${id}`, body)
