/** `lib/api/analytics.ts`. Minimal : le Centre d'Actions vide (pastille de la Sidebar) une projection sans échéance, un reste à vivre nul et aucune répartition de compte. */
import { http, HttpResponse } from "msw"
import { makeActionCenter } from "../factories"
import { apiUrl } from "./apiUrl"

export const analyticsHandlers = [
  http.get(apiUrl("/analytics/actions"), () => HttpResponse.json(makeActionCenter())),
  http.get(apiUrl("/analytics/cashflow-projection"), () =>
    HttpResponse.json({ points: [], events: [], current_balance: 0, projected_balance: 0, low_point: 0, low_point_date: null })),
  http.get(apiUrl("/analytics/diversity-scanner"), () => HttpResponse.json(null)),
  http.get(apiUrl("/analytics/reste-a-vivre"), () => HttpResponse.json({
    revenus_recurrents: 0, charges_essentielles: 0, charges_non_essentielles: 0, reste_a_vivre_essentiel: 0, reste_a_vivre_total: 0,
  })),
]
