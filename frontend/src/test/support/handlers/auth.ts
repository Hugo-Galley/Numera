/** Session : profil (lu par AuthProvider dès qu'un jeton existe), renouvellement, /health (useDemoMode). */
import { http, HttpResponse } from "msw"
import { makeProfile } from "../factories"
import { makeToken } from "../token"
import { apiUrl } from "./apiUrl"

export const authHandlers = [
  http.get(apiUrl("/admin/profile"), () => HttpResponse.json(makeProfile())),
  http.post(apiUrl("/auth/refresh"), () => HttpResponse.json({ access_token: makeToken(), token_type: "bearer" })),
  http.get(apiUrl("/health"), () => HttpResponse.json({ status: "ok", demo: false })),
]
