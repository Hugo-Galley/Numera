/** `lib/api/accounts.ts`. Aucun handler par défaut : chaque test déclare ses réponses avec `server.use(...)`. */
import { http, HttpResponse, type HttpHandler } from "msw"
import { apiUrl } from "./apiUrl"

export const accountsHandlers: HttpHandler[] = []

/** `GET /accounts` → la liste donnée (`server.use(listAccounts([...]))`). */
export const listAccounts = (accounts: object[]) => http.get(apiUrl("/accounts"), () => HttpResponse.json(accounts))
