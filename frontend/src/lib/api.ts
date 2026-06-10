export const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? "/api"
  : "http://localhost:8001"

export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("token")
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })

  if (response.status === 401) {
    localStorage.removeItem("token")
    if (window.location.pathname !== "/login") {
      window.location.href = "/login"
    }
    throw new Error("Session expirée")
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "An error occurred" }))
    throw new Error(error.detail || response.statusText)
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
