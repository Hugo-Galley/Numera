import { renderHook, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { server } from "@/test/server"

// La réponse de /health est mise en cache au niveau du module : un module neuf par test
async function loadHook() {
  vi.resetModules()
  return (await import("./useDemoMode")).useDemoMode
}

/** Compte les appels à /health et répond `response`. */
function healthReturns(response: () => Response) {
  const calls = { count: 0 }
  server.use(
    http.get(apiUrl("/health"), () => {
      calls.count++
      return response()
    }),
  )
  return calls
}

describe("useDemoMode", () => {
  it("vaut true quand /health annonce demo", async () => {
    healthReturns(() => HttpResponse.json({ status: "ok", demo: true }))
    const useDemoMode = await loadHook()
    const { result } = renderHook(() => useDemoMode())
    await waitFor(() => expect(result.current).toBe(true))
  })

  it("vaut false hors démo (réponse par défaut)", async () => {
    const calls = healthReturns(() => HttpResponse.json({ status: "ok", demo: false }))
    const useDemoMode = await loadHook()
    const { result } = renderHook(() => useDemoMode())
    await waitFor(() => expect(calls.count).toBe(1))
    expect(result.current).toBe(false)
  })

  it.each([
    ["une erreur HTTP", () => HttpResponse.json({ demo: true }, { status: 500 })],
    ["une erreur réseau", () => HttpResponse.error()],
  ])("vaut false sur %s", async (_, response) => {
    const calls = healthReturns(response)
    const useDemoMode = await loadHook()
    const { result } = renderHook(() => useDemoMode())
    await waitFor(() => expect(calls.count).toBe(1))
    expect(result.current).toBe(false)
  })

  it("n'interroge /health qu'une fois pour plusieurs composants", async () => {
    const calls = healthReturns(() => HttpResponse.json({ demo: true }))
    const useDemoMode = await loadHook()
    const a = renderHook(() => useDemoMode())
    const b = renderHook(() => useDemoMode())
    await waitFor(() => expect(a.result.current && b.result.current).toBe(true))

    const c = renderHook(() => useDemoMode())
    await waitFor(() => expect(c.result.current).toBe(true))
    expect(calls.count).toBe(1)
  })
})
