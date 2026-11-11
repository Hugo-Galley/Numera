/** Catégories, règles de catégorisation, marchands et tags. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** GET /categories */
export const getCategories = <T = ApiResponse<"/categories", "get">>(query = "") => api.get<T>(`/categories${query}`)

/** POST /categories */
export const postCategories = <T = ApiResponse<"/categories", "post">>(body?: ApiBody<"/categories", "post">) => api.post<T>(`/categories`, body)

/** DELETE /categories/:id */
export const deleteCategoriesById = <T = void>(id: Id) => api.delete<T>(`/categories/${id}`)

/** PATCH /categories/:id */
export const patchCategoriesById = <T = ApiResponse<"/categories/{category_id}", "patch">>(id: Id, body: ApiBody<"/categories/{category_id}", "patch">) => api.patch<T>(`/categories/${id}`, body)

/** POST /categorization-rules/ */
export const postCategorizationRules = <T = ApiResponse<"/categorization-rules/", "post">>(body?: ApiBody<"/categorization-rules/", "post">) => api.post<T>(`/categorization-rules/`, body)

/** GET /merchants */
export const getMerchants = <T = ApiResponse<"/merchants", "get">>() => api.get<T>(`/merchants`)

/** POST /merchants */
export const postMerchants = <T = ApiResponse<"/merchants", "post">>(body?: ApiBody<"/merchants", "post">) => api.post<T>(`/merchants`, body)

/** DELETE /merchants/aliases/:id */
export const deleteMerchantsAliasesById = <T = void>(id: Id) => api.delete<T>(`/merchants/aliases/${id}`)

/** POST /merchants/auto-normalize */
export const postMerchantsAutoNormalize = <T = ApiResponse<"/merchants/auto-normalize", "post">>(body?: unknown) => api.post<T>(`/merchants/auto-normalize`, body)

/** GET /merchants/suggestions/unnormalized */
export const getMerchantsSuggestionsUnnormalized = <T = ApiResponse<"/merchants/suggestions/unnormalized", "get">>(query = "") => api.get<T>(`/merchants/suggestions/unnormalized${query}`)

/** DELETE /merchants/:id */
export const deleteMerchantsById = <T = void>(id: Id) => api.delete<T>(`/merchants/${id}`)

/** GET /merchants/:id */
export const getMerchantsById = <T = ApiResponse<"/merchants/{merchant_id}", "get">>(id: Id) => api.get<T>(`/merchants/${id}`)

/** PUT /merchants/:id */
export const putMerchantsById = <T = ApiResponse<"/merchants/{merchant_id}", "put">>(id: Id, body: ApiBody<"/merchants/{merchant_id}", "put">) => api.put<T>(`/merchants/${id}`, body)

/** POST /merchants/:id/aliases */
export const postMerchantsAliases = <T = ApiResponse<"/merchants/{merchant_id}/aliases", "post">>(id: Id, body?: ApiBody<"/merchants/{merchant_id}/aliases", "post">) => api.post<T>(`/merchants/${id}/aliases`, body)

/** GET /tags */
export const getTags = <T = ApiResponse<"/tags", "get">>() => api.get<T>(`/tags`)
