import { safeStorage } from "@/lib/storage"
import { getTokenExpiry } from "@/lib/utils"

// Dev (vite, port 5173) : API directe sur :8001. Sinon (build servi par nginx, y compris sur
// localhost:8082) : proxy /api. Se baser sur le hostname seul cassait la prod ouverte sur localhost.
export const API_BASE = import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? "http://localhost:8001" : "/api")

export class ApiError extends Error {
  status: number
  detail: any

  constructor(status: number, message: string, detail?: any) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

// Renouvellement glissant : un jeton qui expire dans moins de 15 min est renouvelé au prochain appel.
// L'inactivité reste bornée par l'expiration du jeton, la session entière par SESSION_MAX_HOURS (backend).
const REFRESH_MARGIN_MS = 15 * 60 * 1000
export const TOKEN_REFRESHED_EVENT = "numera:token-refreshed"
let pendingRefresh: Promise<void> | null = null

async function refreshTokenIfNeeded(): Promise<void> {
  const token = safeStorage.getItem("token")
  const expiry = token ? getTokenExpiry(token) : null
  if (!token || !expiry || expiry <= Date.now() || expiry - Date.now() > REFRESH_MARGIN_MS) return
  if (!pendingRefresh) {
    pendingRefresh = fetch(`${API_BASE}/auth/refresh`, { method: "POST", headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) return  // session trop ancienne : le jeton expirera normalement
        const { access_token } = await response.json()
        safeStorage.setItem("token", access_token)
        window.dispatchEvent(new CustomEvent(TOKEN_REFRESHED_EVENT, { detail: access_token }))
      })
      .catch(() => {})
      .finally(() => {
        pendingRefresh = null
      })
  }
  await pendingRefresh
}

/** Message lisible pour l'utilisateur à partir d'une réponse d'erreur (jamais « [object Object] »). */
function formatErrorMessage(response: Response, errorData: any): string {
  const detail = errorData?.detail
  if (typeof detail === "string" && detail) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    // Erreurs de validation FastAPI : « champ : message »
    return detail
      .map((d: any) => {
        const field = Array.isArray(d?.loc) ? d.loc.filter((p: any) => p !== "body" && p !== "query").join(".") : ""
        const text = d?.msg || (typeof d === "string" ? d : JSON.stringify(d))
        return field ? `${field} : ${text}` : text
      })
      .join(" ; ")
  }
  if (detail && typeof detail === "object") return detail.message || detail.detail || "Requête refusée"
  if (typeof errorData?.message === "string" && errorData.message) return errorData.message
  if (response.status >= 500) return `Erreur du serveur (${response.status})`
  return response.statusText || "Une erreur est survenue"
}

async function request(endpoint: string, options?: RequestInit): Promise<Response> {
  if (!endpoint.startsWith("/auth/")) await refreshTokenIfNeeded()
  const token = safeStorage.getItem("token")
  // Pour FormData, le navigateur fixe lui-même Content-Type (boundary multipart)
  const isFormData = typeof FormData !== "undefined" && options?.body instanceof FormData

  let response: Response
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
        ...options?.headers,
      },
    })
  } catch (err) {
    throw new ApiError(0, "Impossible de se connecter au serveur. Vérifiez votre connexion.", err)
  }

  if (response.status === 401 || (response.status === 403 && endpoint !== "/auth/token")) {
    const body = await response.clone().json().catch(() => null)
    // 403 : seuls les jetons de session invalides déconnectent (« User not authorized ») ;
    // un 403 métier (ex. jeton MCP en lecture seule) doit s'afficher comme une erreur ordinaire.
    const isSessionProblem = response.status === 401 || body?.detail === "User not authorized"
    if (isSessionProblem) {
      safeStorage.removeItem("token")
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        const back = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.href = `/login?from=${back}`
      }
      throw new ApiError(response.status, "Session expirée")
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new ApiError(response.status, formatErrorMessage(response, errorData), errorData?.detail)
  }

  return response
}

export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await request(endpoint, options)

  if (response.status === 204) {
    return null as T
  }

  const contentType = response.headers.get("content-type") || ""
  if (!contentType.includes("application/json")) {
    return null as T
  }

  return response.json()
}

/** Télécharge un fichier (CSV, etc.) avec le JWT et retourne le Blob. */
export async function apiDownload(endpoint: string): Promise<Blob> {
  const response = await request(endpoint)
  return response.blob()
}

export const api = {
  get: <T = any>(endpoint: string) => apiFetch<T>(endpoint),
  post: <T = any>(endpoint: string, body?: any) => apiFetch<T>(endpoint, { method: "POST", body: JSON.stringify(body) }),
  put: <T = any>(endpoint: string, body: any) => apiFetch<T>(endpoint, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T = any>(endpoint: string, body: any) => apiFetch<T>(endpoint, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T = any>(endpoint: string) => apiFetch<T>(endpoint, { method: "DELETE" }),
  upload: <T = any>(endpoint: string, formData: FormData) => apiFetch<T>(endpoint, { method: "POST", body: formData }),
  download: apiDownload,
}
