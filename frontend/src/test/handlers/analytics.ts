/** `lib/api/analytics.ts`. Minimal : le Centre d'Actions vide (pastille de la Sidebar). */
import { http, HttpResponse } from "msw"
import { makeActionCenter } from "../factories"
import { apiUrl } from "./apiUrl"

export const analyticsHandlers = [http.get(apiUrl("/analytics/actions"), () => HttpResponse.json(makeActionCenter()))]
