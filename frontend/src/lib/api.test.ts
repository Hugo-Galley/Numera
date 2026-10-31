import { http, HttpResponse } from "msw"
import { API_BASE, ApiError, api, apiFetch } from "./api"
import { safeStorage } from "./storage"
import { apiUrl } from "@/test/handlers"
import { recordRequests } from "@/test/recordRequests"
import { server } from "@/test/server"
import { makeToken } from "@/test/token"

/** Erreur levée par la promesse (échoue si elle est résolue). */
async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  const error = await promise.then(
    () => {
      throw new Error("la promesse aurait dû être rejetée")
    },
    (err: unknown) => err,
  )
  expect(error).toBeInstanceOf(ApiError)
  return error as ApiError
}

describe("apiFetch : en-têtes", () => {
  it("ajoute le Bearer du jeton stocké", async () => {
    const token = makeToken()
    safeStorage.setItem("token", token)
    const requests = recordRequests()

    await apiFetch("/accounts")

    expect(requests[0].headers.get("authorization")).toBe(`Bearer ${token}`)
  })

  it("n'envoie pas d'Authorization sans jeton", async () => {
    const requests = recordRequests()

    await apiFetch("/accounts")

    expect(requests[0].headers.has("authorization")).toBe(false)
  })

  it("envoie Content-Type: application/json par défaut, en GET comme en POST", async () => {
    const requests = recordRequests()

    await api.get("/accounts")
    await api.post("/accounts", { name: "Livret A" })

    expect(requests.map((r) => r.headers.get("content-type"))).toEqual(["application/json", "application/json"])
    expect(requests[1]).toMatchObject({ method: "POST", body: JSON.stringify({ name: "Livret A" }) })
  })

  it("laisse l'appelant surcharger les en-têtes", async () => {
    const requests = recordRequests()

    await apiFetch("/accounts", { headers: { "Content-Type": "text/csv" } })

    expect(requests[0].headers.get("content-type")).toBe("text/csv")
  })
})

describe("API_BASE", () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  async function freshApiBase(): Promise<string> {
    vi.resetModules()
    return (await import("./api")).API_BASE
  }

  it("vaut http://localhost:8001 en développement (serveur Vite)", async () => {
    expect(API_BASE).toBe("http://localhost:8001")
    vi.stubEnv("DEV", true)
    expect(await freshApiBase()).toBe("http://localhost:8001")
  })

  it("vaut /api hors développement (build servi par nginx, même sur localhost)", async () => {
    vi.stubEnv("DEV", false)
    expect(await freshApiBase()).toBe("/api")
  })

  it("VITE_API_BASE l'emporte", async () => {
    vi.stubEnv("DEV", false)
    vi.stubEnv("VITE_API_BASE", "https://numera.example/api")
    expect(await freshApiBase()).toBe("https://numera.example/api")
  })
})

describe("apiFetch : réponses", () => {
  it("renvoie le JSON de la réponse", async () => {
    server.use(http.get(apiUrl("/accounts"), () => HttpResponse.json([{ id: 1 }])))

    expect(await apiFetch("/accounts")).toEqual([{ id: 1 }])
  })

  it("renvoie null pour un 204", async () => {
    server.use(http.delete(apiUrl("/accounts/1"), () => new HttpResponse(null, { status: 204 })))

    expect(await api.delete("/accounts/1")).toBeNull()
  })

  it("renvoie null pour une réponse qui n'est pas du JSON", async () => {
    server.use(http.get(apiUrl("/accounts"), () => HttpResponse.text("ok")))

    expect(await apiFetch("/accounts")).toBeNull()
  })
})

describe("ApiError", () => {
  it("detail texte : message et detail = le texte", async () => {
    server.use(http.post(apiUrl("/transactions"), () => HttpResponse.json({ detail: "Montant invalide" }, { status: 400 })))

    const error = await rejection(api.post("/transactions", {}))

    expect(error).toMatchObject({ name: "ApiError", status: 400, message: "Montant invalide", detail: "Montant invalide" })
  })

  it("detail structuré : message lisible, code et context conservés dans detail", async () => {
    const detail = { code: "MONTH_CLOSED", message: "Mois déjà clôturé", context: { month: "2026-06" } }
    server.use(http.post(apiUrl("/transactions"), () => HttpResponse.json({ detail }, { status: 409 })))

    const error = await rejection(api.post("/transactions", {}))

    expect(error.status).toBe(409)
    expect(error.message).toBe("Mois déjà clôturé")
    expect(error.detail).toEqual(detail)
  })

  it("detail structuré sans message : repli « Requête refusée »", async () => {
    server.use(http.post(apiUrl("/transactions"), () => HttpResponse.json({ detail: { code: "X" } }, { status: 409 })))

    expect((await rejection(api.post("/transactions", {}))).message).toBe("Requête refusée")
  })

  it("erreurs de validation FastAPI : « champ : message » joints par « ; »", async () => {
    const detail = [
      { loc: ["body", "amount"], msg: "doit être positif" },
      { loc: ["query", "month"], msg: "format invalide" },
    ]
    server.use(http.post(apiUrl("/transactions"), () => HttpResponse.json({ detail }, { status: 422 })))

    const error = await rejection(api.post("/transactions", {}))

    expect(error.message).toBe("amount : doit être positif ; month : format invalide")
    expect(error.detail).toEqual(detail)
  })

  it("réponse non JSON en 500 : « Erreur du serveur (500) », sans detail", async () => {
    server.use(http.get(apiUrl("/accounts"), () => HttpResponse.text("Internal Server Error", { status: 500 })))

    const error = await rejection(api.get("/accounts"))

    expect(error).toMatchObject({ status: 500, message: "Erreur du serveur (500)", detail: undefined })
  })

  it("réponse non JSON en 4xx : statusText", async () => {
    server.use(http.get(apiUrl("/accounts"), () => new HttpResponse("<html>", { status: 404, statusText: "Not Found" })))

    expect(await rejection(api.get("/accounts"))).toMatchObject({ status: 404, message: "Not Found" })
  })

  it("erreur réseau : statut 0 et message de connexion", async () => {
    server.use(http.get(apiUrl("/accounts"), () => HttpResponse.error()))

    const error = await rejection(api.get("/accounts"))

    expect(error.status).toBe(0)
    expect(error.message).toBe("Impossible de se connecter au serveur. Vérifiez votre connexion.")
  })
})

describe("api.upload et api.download", () => {
  // setup.ts convertit le FormData de jsdom en FormData natif avant fetch : le corps arrive bien en multipart.
  it("upload : POST sans Content-Type JSON, avec le Bearer", async () => {
    const token = makeToken()
    safeStorage.setItem("token", token)
    const requests = recordRequests()
    const form = new FormData()
    form.append("file", new Blob(["date;montant\n"], { type: "text/csv" }), "releve.csv")

    await api.upload("/import/preview", form)

    expect(requests[0].method).toBe("POST")
    expect(requests[0].headers.get("content-type")).not.toBe("application/json")
    expect(requests[0].headers.get("authorization")).toBe(`Bearer ${token}`)
  })

  it("download : renvoie un Blob, avec le Bearer", async () => {
    const token = makeToken()
    safeStorage.setItem("token", token)
    let authorization: string | null = null
    server.use(
      http.get(apiUrl("/export/transactions"), ({ request }) => {
        authorization = request.headers.get("authorization")
        return HttpResponse.text("date;montant\n2026-06-15;42,50\n", { headers: { "Content-Type": "text/csv" } })
      }),
    )

    const blob = await api.download("/export/transactions")

    // le Blob vient du fetch de Node, pas de jsdom : pas de toBeInstanceOf(Blob)
    expect(Object.prototype.toString.call(blob)).toBe("[object Blob]")
    expect(await blob.text()).toBe("date;montant\n2026-06-15;42,50\n")
    expect(authorization).toBe(`Bearer ${token}`)
  })

  it("download : une erreur HTTP lève ApiError", async () => {
    server.use(http.get(apiUrl("/export/transactions"), () => HttpResponse.json({ detail: "Rien à exporter" }, { status: 404 })))

    expect(await rejection(api.download("/export/transactions"))).toMatchObject({ status: 404, message: "Rien à exporter" })
  })
})
