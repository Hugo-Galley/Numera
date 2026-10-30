import { http, HttpResponse } from "msw"
import { ApiError, TOKEN_REFRESHED_EVENT, api } from "./api"
import { safeStorage } from "./storage"
import { apiUrl } from "@/test/handlers"
import { recordRequests } from "@/test/recordRequests"
import { server } from "@/test/server"
import { makeToken } from "@/test/token"

/** `window.location` remplacé par un objet simple : jsdom n'implémente pas la navigation. */
function fakeLocation(pathname: string, search = "") {
  const location = { pathname, search, href: `http://localhost:3000${pathname}${search}` }
  vi.spyOn(window, "location", "get").mockReturnValue(location as unknown as Location)
  return location
}

function respondWith(status: number, body: unknown = null) {
  server.use(http.get(apiUrl("/accounts"), () => (body === null ? new HttpResponse(null, { status }) : HttpResponse.json(body, { status }))))
}

async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  const error = await promise.then(() => null, (err: unknown) => err)
  expect(error).toBeInstanceOf(ApiError)
  return error as ApiError
}

describe("session : 401 et 403", () => {
  beforeEach(() => safeStorage.setItem("token", makeToken()))

  it("401 : vide la session et redirige vers /login en gardant l'adresse de retour", async () => {
    const location = fakeLocation("/accounts/3", "?tab=history")
    respondWith(401, { detail: "Not authenticated" })

    const error = await rejection(api.get("/accounts"))

    expect(error).toMatchObject({ status: 401, message: "Session expirée" })
    expect(safeStorage.getItem("token")).toBeNull()
    expect(location.href).toBe("/login?from=%2Faccounts%2F3%3Ftab%3Dhistory")
  })

  it("401 sur la page de connexion : vide la session sans rediriger", async () => {
    const location = fakeLocation("/login")
    respondWith(401)

    await rejection(api.get("/accounts"))

    expect(safeStorage.getItem("token")).toBeNull()
    expect(location.href).toBe("http://localhost:3000/login")
  })

  it("403 « User not authorized » (jeton de session invalide) : même déconnexion qu'un 401", async () => {
    const location = fakeLocation("/settings")
    respondWith(403, { detail: "User not authorized" })

    expect(await rejection(api.get("/accounts"))).toMatchObject({ status: 403, message: "Session expirée" })
    expect(safeStorage.getItem("token")).toBeNull()
    expect(location.href).toBe("/login?from=%2Fsettings")
  })

  it("403 métier (ex. jeton MCP en lecture seule) : erreur ordinaire, session gardée", async () => {
    const location = fakeLocation("/settings")
    respondWith(403, { detail: "Jeton MCP en lecture seule" })

    expect(await rejection(api.get("/accounts"))).toMatchObject({ status: 403, message: "Jeton MCP en lecture seule" })
    expect(safeStorage.getItem("token")).not.toBeNull()
    expect(location.href).toBe("http://localhost:3000/settings")
  })

  it("403 sur /auth/token (mauvais identifiants) : jamais de déconnexion", async () => {
    const location = fakeLocation("/login")
    server.use(http.post(apiUrl("/auth/token"), () => HttpResponse.json({ detail: "User not authorized" }, { status: 403 })))

    expect(await rejection(api.post("/auth/token", {}))).toMatchObject({ status: 403, message: "User not authorized" })
    expect(safeStorage.getItem("token")).not.toBeNull()
    expect(location.href).toBe("http://localhost:3000/login")
  })
})

describe("session : renouvellement du jeton", () => {
  /** Compte les appels à POST /auth/refresh et répond selon `status` (à poser après `recordRequests`, qui sinon les intercepte). */
  function refreshEndpoint(status = 200, newToken = makeToken({ expInMinutes: 60, sub: "renouvele" })) {
    const calls: (string | null)[] = []
    server.use(
      http.post(apiUrl("/auth/refresh"), ({ request }) => {
        calls.push(request.headers.get("authorization"))
        return status === 200 ? HttpResponse.json({ access_token: newToken, token_type: "bearer" }) : new HttpResponse(null, { status })
      }),
    )
    return { calls, newToken }
  }

  it("moins de 15 min restantes : renouvelle avant l'appel, qui part avec le nouveau jeton", async () => {
    const oldToken = makeToken({ expInMinutes: 10 })
    safeStorage.setItem("token", oldToken)
    const requests = recordRequests()
    const { calls, newToken } = refreshEndpoint()
    const refreshed = vi.fn()
    window.addEventListener(TOKEN_REFRESHED_EVENT, refreshed)

    await api.get("/accounts")
    window.removeEventListener(TOKEN_REFRESHED_EVENT, refreshed)

    expect(calls).toEqual([`Bearer ${oldToken}`])
    expect(safeStorage.getItem("token")).toBe(newToken)
    expect(requests.map((r) => [r.path, r.headers.get("authorization")])).toEqual([["/accounts", `Bearer ${newToken}`]])
    expect((refreshed.mock.calls[0][0] as CustomEvent).detail).toBe(newToken)
  })

  it("plus de 15 min restantes : pas de renouvellement", async () => {
    safeStorage.setItem("token", makeToken({ expInMinutes: 20 }))
    recordRequests()
    const { calls } = refreshEndpoint()

    await api.get("/accounts")

    expect(calls).toHaveLength(0)
  })

  it("jeton déjà expiré : pas de renouvellement", async () => {
    safeStorage.setItem("token", makeToken({ expInMinutes: -1 }))
    recordRequests()
    const { calls } = refreshEndpoint()

    await api.get("/accounts")

    expect(calls).toHaveLength(0)
  })

  it("appels simultanés : un seul renouvellement", async () => {
    safeStorage.setItem("token", makeToken({ expInMinutes: 5 }))
    recordRequests()
    const { calls } = refreshEndpoint()

    await Promise.all([api.get("/accounts"), api.get("/transactions"), api.get("/goals")])

    expect(calls).toHaveLength(1)
  })

  it("renouvellement refusé : un seul essai, l'appel part avec l'ancien jeton qui reste en place", async () => {
    const oldToken = makeToken({ expInMinutes: 10 })
    safeStorage.setItem("token", oldToken)
    const requests = recordRequests()
    const { calls } = refreshEndpoint(401)

    await api.get("/accounts")

    expect(calls).toHaveLength(1)
    expect(safeStorage.getItem("token")).toBe(oldToken)
    expect(requests.map((r) => r.headers.get("authorization"))).toEqual([`Bearer ${oldToken}`])
  })

  it("routes /auth/* : jamais de renouvellement (pas de boucle sur /auth/refresh)", async () => {
    safeStorage.setItem("token", makeToken({ expInMinutes: 10 }))
    const { calls } = refreshEndpoint()
    server.use(http.get(apiUrl("/auth/passkey/status"), () => HttpResponse.json({})))

    await api.get("/auth/passkey/status")

    expect(calls).toHaveLength(0)
  })
})
