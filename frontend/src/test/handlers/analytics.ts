/** `lib/api/analytics.ts`. Minimal : le Centre d'Actions vide (pastille de la Sidebar) et une projection sans échéance. */
import { http, HttpResponse } from "msw"
import { makeActionCenter } from "../factories"
import { apiUrl } from "./apiUrl"

export const analyticsHandlers = [
  http.get(apiUrl("/analytics/actions"), () => HttpResponse.json(makeActionCenter())),
  http.get(apiUrl("/analytics/cashflow-projection"), () =>
    HttpResponse.json({ points: [], events: [], current_balance: 0, projected_balance: 0, low_point: 0, low_point_date: null })),
]
