import type { paths } from "./generated/schema"

/** Identifiant interpolé dans une route (`/accounts/${id}`). */
export type Id = string | number

/**
 * Types du contrat API, générés depuis le schéma OpenAPI du backend (`make api-contract`).
 * `ApiResponse<"/accounts", "get">` : corps JSON de la réponse 200/201 ; `ApiBody<"/accounts", "post">` : corps de la requête.
 * Un renommage de champ côté backend casse alors `tsc` au lieu de produire un `undefined` à l'exécution.
 */
type Json<R> = R extends { content: { "application/json": infer B } } ? B : never
type Responses<P extends keyof paths, M extends keyof paths[P]> = paths[P][M] extends { responses: infer R } ? R : never

export type ApiResponse<P extends keyof paths, M extends keyof paths[P]> = Json<
  Responses<P, M> extends { 200: infer R } ? R : Responses<P, M> extends { 201: infer R } ? R : never
>
export type ApiBody<P extends keyof paths, M extends keyof paths[P]> = paths[P][M] extends { requestBody?: infer B }
  ? Json<NonNullable<B>>
  : never
