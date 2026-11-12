/** Revue de fin de mois. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse } from "./types"

/** GET /month-review/closures */
export const getMonthReviewClosures = <T = ApiResponse<"/month-review/closures", "get">>() => api.get<T>(`/month-review/closures`)

/** GET /month-review */
export const getMonthReview = <T = ApiResponse<"/month-review", "get">>(query = "") => api.get<T>(`/month-review${query}`)

/** POST /month-review/close */
export const postMonthReviewClose = <T = ApiResponse<"/month-review/close", "post">>(body?: ApiBody<"/month-review/close", "post">) => api.post<T>(`/month-review/close`, body)

/** DELETE /month-review */
export const deleteMonthReview = <T = void>(query = "") => api.delete<T>(`/month-review${query}`)
