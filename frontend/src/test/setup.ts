/** Chargé avant chaque fichier de test (vitest.config.ts) : matchers, polyfills jsdom, serveur MSW. */
import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
import { File as NodeFile } from "node:buffer"
import { server } from "./server"

// jsdom n'implémente pas ces API, utilisées par Radix (Dialog, Select…) et Recharts
if (!window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })
}

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver

class IntersectionObserverStub {
  readonly root = null
  readonly rootMargin = "0px"
  readonly thresholds: number[] = []
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
}
globalThis.IntersectionObserver ??= IntersectionObserverStub as unknown as typeof IntersectionObserver

Element.prototype.scrollIntoView ??= function () {}
Element.prototype.scrollTo ??= function () {}
Element.prototype.hasPointerCapture ??= () => false
Element.prototype.setPointerCapture ??= function () {}
Element.prototype.releasePointerCapture ??= function () {}

// jsdom remplace FormData, URLSearchParams, Blob et File par ses propres classes ; le fetch de Node (undici) ne les
// reconnaît pas toujours selon la version (Node 22 : corps envoyé en « [object FormData] » ou requête bloquée).
// On les convertit en classes natives à la frontière fetch, sans toucher au code de l'application.
const NativeFormData = (await new Response("a=1", { headers: { "content-type": "application/x-www-form-urlencoded" } }).formData()).constructor as typeof FormData

async function toNativeBody(init?: RequestInit): Promise<RequestInit | undefined> {
  const body = init?.body
  if (body instanceof URLSearchParams) {
    const headers = new Headers(init?.headers)
    if (!headers.has("content-type")) headers.set("content-type", "application/x-www-form-urlencoded;charset=UTF-8")
    return { ...init, headers, body: body.toString() }
  }
  if (body instanceof FormData) {
    const native = new NativeFormData()
    for (const [name, value] of body.entries()) {
      if (typeof value === "string") native.append(name, value)
      else native.append(name, new NodeFile([await value.arrayBuffer()], value.name, { type: value.type }) as unknown as Blob, value.name)
    }
    return { ...init, body: native }
  }
  return init
}

let mswFetch: typeof fetch

// Toute requête sans handler fait échouer le test, même si le composant avale l'erreur réseau
const unhandledRequests: string[] = []
beforeAll(() => {
  server.listen({
    onUnhandledRequest(request, print) {
      unhandledRequests.push(`${request.method} ${request.url}`)
      print.error()
    },
  })
  mswFetch = globalThis.fetch
  globalThis.fetch = async (input, init) => mswFetch(input, await toNativeBody(init))
})

afterEach(() => {
  cleanup()
  server.resetHandlers()
  window.localStorage.clear()
  window.sessionStorage.clear()
  if (unhandledRequests.length) {
    throw new Error(`Requête(s) sans handler MSW : ${unhandledRequests.splice(0).join(", ")}`)
  }
})

afterAll(() => {
  globalThis.fetch = mswFetch
  server.close()
})
