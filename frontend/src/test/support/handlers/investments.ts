/** `lib/api/investments.ts`. Chaque test déclare ses réponses avec `server.use(...)` ou complète ce fichier. */
import { http, HttpResponse, type HttpHandler } from "msw"
import { apiUrl } from "./apiUrl"

export const investmentsHandlers: HttpHandler[] = [
  // Page d'un compte titres : aucun versement automatique à relier par défaut
  http.get(apiUrl("/investment-transactions"), () => HttpResponse.json([])),
]
