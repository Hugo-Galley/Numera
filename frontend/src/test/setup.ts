/** Chargé avant chaque fichier de test (vitest.config.ts) : matchers, polyfills jsdom, serveur MSW. */
import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
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
Element.prototype.hasPointerCapture ??= () => false
Element.prototype.setPointerCapture ??= function () {}
Element.prototype.releasePointerCapture ??= function () {}

// Toute requête sans handler fait échouer le test, même si le composant avale l'erreur réseau
const unhandledRequests: string[] = []
beforeAll(() =>
  server.listen({
    onUnhandledRequest(request, print) {
      unhandledRequests.push(`${request.method} ${request.url}`)
      print.error()
    },
  }),
)

afterEach(() => {
  cleanup()
  server.resetHandlers()
  window.localStorage.clear()
  window.sessionStorage.clear()
  if (unhandledRequests.length) {
    throw new Error(`Requête(s) sans handler MSW : ${unhandledRequests.splice(0).join(", ")}`)
  }
})

afterAll(() => server.close())
