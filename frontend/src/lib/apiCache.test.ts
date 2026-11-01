import { http, HttpResponse } from "msw"
import { api } from "./api"
import { apiUrl } from "@/test/handlers"
import { server } from "@/test/server"

/** Handler qui compte les requêtes reçues par chemin et répond avec un compteur. */
function countingServer() {
  const hits: Record<string, number> = {}
  server.use(
    http.all(apiUrl("/*"), ({ request }) => {
      const path = new URL(request.url).pathname.replace(/^.*\/api/, "")
      hits[request.method + " " + path] = (hits[request.method + " " + path] ?? 0) + 1
      return HttpResponse.json({ n: hits[request.method + " " + path], items: [1, 2, 3] })
    }),
  )
  return hits
}

describe("api.get : cache bref et dédoublonnage", () => {
  it("sert la deuxième lecture du même chemin sans requête réseau", async () => {
    const hits = countingServer()

    const first = await api.get("/accounts")
    const second = await api.get("/accounts")

    expect(second).toEqual(first)
    expect(hits["GET /accounts"]).toBe(1)
  })

  it("dédoublonne deux lectures simultanées du même chemin", async () => {
    const hits = countingServer()

    await Promise.all([api.get("/accounts"), api.get("/accounts")])

    expect(hits["GET /accounts"]).toBe(1)
  })

  it("distingue les chemins et les query strings", async () => {
    const hits = countingServer()

    await api.get("/analytics/budget?month=1")
    await api.get("/analytics/budget?month=2")

    expect(hits["GET /analytics/budget"]).toBe(2)
  })

  it("une écriture (POST, PATCH, PUT, DELETE) vide le cache", async () => {
    const hits = countingServer()
    await api.get("/accounts")

    await api.patch("/accounts/1", { name: "x" })
    await api.get("/accounts")

    expect(hits["GET /accounts"]).toBe(2)
  })

  it("une lecture lancée avant une écriture ne repeuple pas le cache avec l'ancien état", async () => {
    const hits = countingServer()
    const slowRead = api.get("/accounts")

    await api.post("/accounts", { name: "nouveau" })
    await slowRead
    await api.get("/accounts")

    expect(hits["GET /accounts"]).toBe(2)
  })

  it("modifier la réponse reçue ne corrompt pas le cache", async () => {
    countingServer()
    const first = await api.get<{ items: number[] }>("/accounts")
    first.items.push(99)

    const second = await api.get<{ items: number[] }>("/accounts")

    expect(second.items).toEqual([1, 2, 3])
  })

  it("ne mémorise pas une erreur", async () => {
    let calls = 0
    server.use(
      http.get(apiUrl("/accounts"), () => {
        calls += 1
        return calls === 1 ? HttpResponse.json({ detail: "boom" }, { status: 500 }) : HttpResponse.json([])
      }),
    )

    await expect(api.get("/accounts")).rejects.toThrow()
    await expect(api.get("/accounts")).resolves.toEqual([])
    expect(calls).toBe(2)
  })
})
