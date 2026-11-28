/** `lib/api/monthReview.ts`. Aucun handler par défaut : chaque test déclare ses réponses avec `server.use(...)`. */
import { http, HttpResponse, type HttpHandler } from "msw"
import { apiUrl } from "./apiUrl"

export const monthReviewHandlers: HttpHandler[] = []

/** `POST /month-review/accounts/confirm-unchanged` → la revue donnée ; chaque corps reçu est ajouté à `bodies`. */
export const confirmUnchangedAccounts = (review: object, bodies: unknown[] = []) =>
  http.post(apiUrl("/month-review/accounts/confirm-unchanged"), async ({ request }) => {
    bodies.push(await request.json())
    return HttpResponse.json(review)
  })
