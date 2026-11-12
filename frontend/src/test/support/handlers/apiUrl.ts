import { API_BASE } from "@/lib/api"

/** URL complète d'une route backend, telle que l'appelle `lib/api.ts` (`apiUrl("/accounts")`). */
export const apiUrl = (path: string) => `${API_BASE}${path}`
