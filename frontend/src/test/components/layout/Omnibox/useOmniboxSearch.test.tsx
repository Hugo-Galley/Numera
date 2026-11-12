/** Recherche de l'Omnibox : comptes, transactions (anti-rebond), saisie rapide, actions et navigation clavier. */
import type { ReactNode } from "react"
import { act, renderHook, waitFor } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { MemoryRouter, useLocation } from "react-router-dom"
import { toast } from "sonner"
import { resetApiCache } from "@/lib/apiCache"
import { useOmniboxSearch } from "@/components/layout/Omnibox/useOmniboxSearch"
import { UIProvider } from "@/providers/UIProvider"
import { apiUrl } from "@/test/support/handlers"
import { server } from "@/test/support/server"

const accounts = [
  { id: 1, name: "Compte joint", type: "courant", active: true, is_main: false },
  { id: 2, name: "Livret A", type: "epargne", active: true, is_main: false },
  { id: 3, name: "Compte principal", type: "courant", active: true, is_main: true },
]

let location: ReturnType<typeof useLocation>
function Spy() { location = useLocation(); return null }
const wrapper = ({ children }: { children: ReactNode }) => (
  <UIProvider><MemoryRouter><Spy />{children}</MemoryRouter></UIProvider>
)

/** Hook monté, recherche ouverte (charge les comptes). */
async function open(accountList: object[] = accounts) {
  resetApiCache() // lecture mise en cache 30 s : chaque ouverture repart d'une liste neuve
  server.use(http.get(apiUrl("/accounts"), () => HttpResponse.json(accountList)))
  const view = renderHook(() => useOmniboxSearch(), { wrapper })
  act(() => view.result.current.setSearchOpen(true))
  await waitFor(() => expect(view.result.current.accounts).toHaveLength(accountList.length))
  return view
}

const types = (r: { current: ReturnType<typeof useOmniboxSearch> }) => r.current.results.map((x: { type: string }) => x.type)

describe("useOmniboxSearch", () => {
  it("requête vide : toute la navigation, les comptes et les actions, aucune transaction", async () => {
    const { result } = await open()

    expect(result.current.filteredAccounts.map((a) => a.name)).toEqual(["Compte joint", "Livret A", "Compte principal"])
    expect(result.current.filteredNavigation.length).toBeGreaterThan(10)
    expect(result.current.filteredActions).toHaveLength(5)
    expect(result.current.quickResults).toEqual([])
    expect(result.current.mainAccount?.name).toBe("Compte principal")
  })

  it("filtre sans casse sur comptes, navigation et actions", async () => {
    const { result } = await open()

    act(() => result.current.setQuery("livret"))

    expect(result.current.filteredAccounts.map((a) => a.name)).toEqual(["Livret A"])
    expect(result.current.filteredActions).toEqual([])
  })

  it("compte principal : à défaut, premier compte courant actif ; aucun → toast au lieu d'une navigation", async () => {
    const { result } = await open([{ id: 9, name: "Inactif", type: "courant", active: false }, { id: 8, name: "Courant 8", type: "courant", active: true }])
    expect(result.current.mainAccount?.id).toBe(8)

    const error = vi.spyOn(toast, "error")
    const empty = await open([{ id: 2, name: "Livret", type: "epargne", active: true }])
    act(() => empty.result.current.openNewTransaction())
    expect(error).toHaveBeenCalledTimes(1)
  })

  it("moins de deux caractères : pas de recherche ; au-delà, recherche après anti-rebond avec la requête encodée", async () => {
    const urls: string[] = []
    const { result } = await open()
    server.use(http.get(apiUrl("/transactions"), ({ request }) => { urls.push(request.url); return HttpResponse.json([{ id: 5, account_id: 2, type: "Sortie", merchant: "Café" }]) }))

    act(() => result.current.setQuery("c"))
    await new Promise((r) => setTimeout(r, 400))
    expect(urls).toEqual([])

    act(() => result.current.setQuery("café & co"))
    await waitFor(() => expect(result.current.transactions).toHaveLength(1))
    expect(new URL(urls[0]).searchParams.get("search")).toBe("café & co")
    expect(new URL(urls[0]).searchParams.get("limit")).toBe("10")
    expect(result.current.loading).toBe(false)
    expect(result.current.results.slice(-1)[0]).toMatchObject({ type: "transaction", txType: "Sortie", id: 5 })
  })

  it("échec de la recherche : drapeau levé, liste vidée, levé de nouveau dès que la requête redevient courte", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {})
    const { result } = await open()
    server.use(http.get(apiUrl("/transactions"), () => new HttpResponse(null, { status: 500 })))

    act(() => result.current.setQuery("loyer"))
    await waitFor(() => expect(result.current.searchFailed).toBe(true))
    expect(result.current.transactions).toEqual([])

    act(() => result.current.setQuery(""))
    await waitFor(() => expect(result.current.searchFailed).toBe(false))
  })

  it("saisie rapide : « 12,50 boulangerie » → dépense ; « +1200 prime » → revenu", async () => {
    const { result } = await open()

    act(() => result.current.setQuery("12,50 boulangerie"))
    expect(result.current.quickEntry).toEqual({ amount: 12.5, type: "Sortie", merchant: "boulangerie" })

    act(() => result.current.setQuery("+1200 prime"))
    expect(result.current.quickEntry).toMatchObject({ amount: 1200, type: "Entree", merchant: "prime" })
    expect(types(result)).toContain("quick")
  })

  it("sélection : navigation, compte, saisie rapide (compte principal, paramètres), ferme la recherche", async () => {
    const { result } = await open()

    act(() => result.current.handleSelect(result.current.filteredNavigation.find((n) => n.href === "/savings")))
    expect(location.pathname).toBe("/savings")
    expect(result.current.isSearchOpen).toBe(false)

    act(() => result.current.handleSelect({ type: "account", id: 2 }))
    expect(location.pathname).toBe("/accounts/2")

    act(() => result.current.handleSelect({ type: "quick", entryType: "Sortie", amount: 12.5, merchant: "Pain" }))
    expect(location.pathname).toBe("/accounts/3")
    expect(Object.fromEntries(new URLSearchParams(location.search))).toEqual({ new: "tx", type: "Sortie", amount: "12.5", merchant: "Pain" })
  })

  it("sélection d'une transaction : ouverte en modification dans son compte, avec son vrai type", async () => {
    const { result } = await open()

    act(() => result.current.handleSelect(result.current.asTransactionResult({ id: 5, account_id: 2, type: "Entree", merchant: "Salaire" })))

    expect(location.pathname).toBe("/accounts/2")
    expect(location.state).toEqual({ openTransaction: { id: 5, account_id: 2, type: "Entree", merchant: "Salaire" } })
  })

  it("actions : import, revue, prêt et bascule du mode confidentialité (libellé inversé)", async () => {
    const { result } = await open()
    const run = (id: string) => act(() => result.current.handleSelect(result.current.filteredActions.find((a) => a.id === id)))

    run("import")
    expect(location.pathname + location.search).toBe("/accounts?import=1")
    run("review")
    expect(location.pathname).toBe("/month/revue")
    run("loan")
    expect(location.pathname + location.search).toBe("/accounts?new=loan")

    const before = result.current.filteredActions.find((a) => a.id === "privacy")!.name
    run("privacy")
    expect(result.current.isPrivacyMode).toBe(true)
    expect(result.current.filteredActions.find((a) => a.id === "privacy")!.name).not.toBe(before)
    // « Nouvelle transaction » : indique le compte utilisé
    expect(result.current.filteredActions.find((a) => a.id === "new-tx")!.hint).toBe("Compte principal")
  })

  it("clavier : flèches circulaires, Entrée ouvre le résultat actif", async () => {
    const { result } = await open()
    const key = (k: string) => act(() => result.current.handleKeyDown({ key: k, preventDefault: vi.fn() } as never))
    const total = result.current.results.length

    key("ArrowUp")
    expect(result.current.activeIndex).toBe(total - 1)
    key("ArrowDown")
    expect(result.current.activeIndex).toBe(0)
    key("ArrowDown")
    expect(result.current.activeIndex).toBe(1)

    key("Enter")
    expect(location.pathname).toBe(result.current.results[1].type === "nav" ? (result.current.results[1] as { href: string }).href : location.pathname)
    expect(result.current.isSearchOpen).toBe(false)
  })

  it("rouvrir la recherche remet la requête et la sélection à zéro", async () => {
    const { result } = await open()
    act(() => { result.current.setQuery("abc"); result.current.setActiveIndex(2) })
    act(() => result.current.setSearchOpen(false))
    act(() => result.current.setSearchOpen(true))

    expect(result.current.query).toBe("")
    expect(result.current.activeIndex).toBe(0)
  })

  it("mobile : suit la zone visible (clavier virtuel) tant que la recherche est ouverte", async () => {
    const listeners: Record<string, () => void> = {}
    const vv = { height: 500, offsetTop: 10, addEventListener: (e: string, f: () => void) => { listeners[e] = f }, removeEventListener: vi.fn() }
    vi.stubGlobal("visualViewport", vv)
    try {
      const { result } = await open()
      expect(result.current.viewport).toEqual({ height: 500, top: 10 })

      vv.height = 300
      act(() => listeners.resize())
      expect(result.current.viewport).toEqual({ height: 300, top: 10 })
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it("échec du chargement des comptes : la recherche reste utilisable", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {})
    server.use(http.get(apiUrl("/accounts"), () => new HttpResponse(null, { status: 500 })))
    const { result } = renderHook(() => useOmniboxSearch(), { wrapper })

    act(() => result.current.setSearchOpen(true))
    await waitFor(() => expect(console.error).toHaveBeenCalled())

    expect(result.current.accounts).toEqual([])
    expect(result.current.filteredNavigation.length).toBeGreaterThan(0)
  })
})
