/** `lib/api/transactions.ts`. Aucun handler par défaut : chaque test déclare ses réponses avec `server.use(...)`. */
import { http, HttpResponse, type HttpHandler } from "msw"
import { apiUrl } from "./apiUrl"

export const transactionsHandlers: HttpHandler[] = []

/** `GET /transactions?search=…` → les transactions données, quelle que soit la query. */
export const searchTransactions = (transactions: object[] = []) =>
  http.get(apiUrl("/transactions"), () => HttpResponse.json(transactions))
