/** Enregistre toutes les requêtes vers l'API (handler « attrape-tout » posé par `server.use`), pour vérifier méthode, URL, query, en-têtes et corps. */
import { http, HttpResponse } from "msw"
import { apiUrl } from "./handlers"
import { server } from "./server"

export interface RecordedRequest {
  method: string
  /** Chemin relatif à `API_BASE` (« /accounts/1 »), sans la query. */
  path: string
  /** Query brute, `?` compris (« ?month=2026-06 »), chaîne vide sinon. */
  search: string
  headers: Headers
  /** Corps brut (texte), `null` si absent. */
  body: string | null
}

/** Répond `{}` en JSON à toute requête API et la consigne dans le tableau renvoyé. */
export function recordRequests(): RecordedRequest[] {
  const requests: RecordedRequest[] = []
  const base = new URL(apiUrl("/")).pathname.replace(/\/$/, "")
  server.use(
    http.all(apiUrl("/*"), async ({ request }) => {
      const url = new URL(request.url)
      const text = await request.text()
      requests.push({
        method: request.method,
        path: url.pathname.slice(base.length),
        search: url.search,
        headers: request.headers,
        body: text === "" ? null : text,
      })
      return HttpResponse.json({})
    }),
  )
  return requests
}
