export const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? "/api"
  : "http://localhost:8001"

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

export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("token")
  
  let response: Response
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
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

  if (response.status === 204) {
    return null as T
  }

  const contentType = response.headers.get("content-type") || ""
  if (!contentType.includes("application/json")) {
    return null as T
  }

  return response.json()
}

export const api = {
  get: <T>(endpoint: string) => apiFetch<T>(endpoint),
  post: <T>(endpoint: string, body: any) => apiFetch<T>(endpoint, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(endpoint: string, body: any) => apiFetch<T>(endpoint, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(endpoint: string, body: any) => apiFetch<T>(endpoint, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(endpoint: string) => apiFetch<T>(endpoint, { method: "DELETE" }),
}
