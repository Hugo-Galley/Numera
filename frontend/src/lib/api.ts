// Dev (vite, port 5173) : API directe sur :8001. Sinon (build servi par nginx, y compris sur
// localhost:8082) : proxy /api. Se baser sur le hostname seul cassait la prod ouverte sur localhost.
export const API_BASE = import.meta.env.DEV ? "http://localhost:8001" : "/api"

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

async function request(endpoint: string, options?: RequestInit): Promise<Response> {
  const token = localStorage.getItem("token")
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
    localStorage.removeItem("token")
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login"
    }
    throw new ApiError(response.status, "Session expirée")
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }))
    let errorMessage = "Une erreur est survenue"
    
    if (typeof errorData?.detail === "string") {
      errorMessage = errorData.detail
    } else if (Array.isArray(errorData?.detail)) {
      // Format FastAPI 422 validation errors cleanly
      errorMessage = errorData.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ")
    } else if (errorData?.message) {
      errorMessage = errorData.message
    } else if (response.statusText) {
      errorMessage = response.statusText
    }

    throw new ApiError(response.status, errorMessage, errorData?.detail)
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
