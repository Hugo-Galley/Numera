/** Catégories, règles de catégorisation, marchands et tags. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { Id } from "./types"

/** GET /categories */
export const getCategories = <T = any>(query = "") => api.get<T>(`/categories${query}`)

/** POST /categories */
export const postCategories = <T = any>(body?: any) => api.post<T>(`/categories`, body)

/** DELETE /categories/:id */
export const deleteCategoriesById = <T = any>(id: Id) => api.delete<T>(`/categories/${id}`)

/** PATCH /categories/:id */
export const patchCategoriesById = <T = any>(id: Id, body: any) => api.patch<T>(`/categories/${id}`, body)

/** POST /categorization-rules */
export const postCategorizationRules = <T = any>(body?: any) => api.post<T>(`/categorization-rules`, body)

/** GET /merchants */
export const getMerchants = <T = any>() => api.get<T>(`/merchants`)

/** POST /merchants */
export const postMerchants = <T = any>(body?: any) => api.post<T>(`/merchants`, body)

/** DELETE /merchants/aliases/:id */
export const deleteMerchantsAliasesById = <T = any>(id: Id) => api.delete<T>(`/merchants/aliases/${id}`)

/** POST /merchants/auto-normalize */
export const postMerchantsAutoNormalize = <T = any>(body?: any) => api.post<T>(`/merchants/auto-normalize`, body)

/** GET /merchants/suggestions/unnormalized */
export const getMerchantsSuggestionsUnnormalized = <T = any>(query = "") => api.get<T>(`/merchants/suggestions/unnormalized${query}`)

/** DELETE /merchants/:id */
export const deleteMerchantsById = <T = any>(id: Id) => api.delete<T>(`/merchants/${id}`)

/** GET /merchants/:id */
export const getMerchantsById = <T = any>(id: Id) => api.get<T>(`/merchants/${id}`)

/** PUT /merchants/:id */
export const putMerchantsById = <T = any>(id: Id, body: any) => api.put<T>(`/merchants/${id}`, body)

/** POST /merchants/:id/aliases */
export const postMerchantsAliases = <T = any>(id: Id, body?: any) => api.post<T>(`/merchants/${id}/aliases`, body)

/** GET /tags */
export const getTags = <T = any>() => api.get<T>(`/tags`)
