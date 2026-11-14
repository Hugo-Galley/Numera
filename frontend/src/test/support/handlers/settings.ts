/** Réglages : enregistrement de la langue des notifications (envoyé à chaque changement de langue). */
import { http, HttpResponse } from "msw"
import { apiUrl } from "./apiUrl"

export const settingsHandlers = [http.put(apiUrl("/notifications/settings"), () => HttpResponse.json({}))]
