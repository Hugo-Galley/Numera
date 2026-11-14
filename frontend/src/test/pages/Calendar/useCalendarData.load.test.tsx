/** Calendrier : mois affiché, filtre de compte, grille, échecs de chargement et validation d'une échéance d'investissement. */
import type { ReactNode } from "react"
import { act, renderHook, screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Toaster } from "@/components/ui/sonner"
import { resetApiCache } from "@/lib/apiCache"
import { UIProvider } from "@/providers/UIProvider"
import type { CalendarData, CalendarEvent } from "@/pages/Calendar/types"
import { useCalendarData } from "@/pages/Calendar/useCalendarData"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { server } from "@/test/support/server"

const wrapper = ({ children }: { children: ReactNode }) => <UIProvider>{children}<Toaster /></UIProvider>

const event = (over: Partial<CalendarEvent> = {}): CalendarEvent => ({
  id: "e1", date: "2026-06-20T00:00:00", name: "Loyer", amount: 850, type: "Sortie", category_id: 3, is_projected: true, currency: "EUR", recurring_id: 7, ...over,
})
const calendar = (events: CalendarEvent[] = [event()]): CalendarData => ({
  month: 6, year: 2026, events, daily_balances: [{ date: "2026-06-20", balance: 1234 }],
})

function serve({ events = [event()], accounts = [makeAccount({ id: 1 })] }: { events?: CalendarEvent[]; accounts?: object[] } = {}) {
  const queries: string[] = []
  server.use(
    http.get(apiUrl("/accounts"), () => HttpResponse.json(accounts)),
    http.get(apiUrl("/analytics/calendar"), ({ request }) => { queries.push(new URL(request.url).search); return HttpResponse.json(calendar(events)) }),
  )
  return queries
}

beforeEach(() => {
  resetApiCache()
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date(2026, 5, 15))
  vi.spyOn(console, "error").mockImplementation(() => {})
})
afterEach(() => vi.useRealTimers())

const loaded = async (r: { current: ReturnType<typeof useCalendarData> }) => waitFor(() => expect(r.current.data).not.toBeNull())

describe("useCalendarData : affichage", () => {
  it("charge le mois courant, calcule la grille (lundi en premier) et les événements/soldes d'un jour", async () => {
    const queries = serve()
    const { result } = renderHook(() => useCalendarData(), { wrapper })
    await loaded(result)

    expect(queries[0]).toBe("?month=6&year=2026")
    // 1er juin 2026 = lundi : aucune case vide avant ; 30 jours
    expect(result.current.startingDay).toBe(0)
    expect(result.current.calendarDays).toHaveLength(30)
    expect(result.current.getEventsForDay(20)).toHaveLength(1)
    expect(result.current.getEventsForDay(21)).toEqual([])
    expect(result.current.getBalanceForDay(20)).toBe(1234)
    expect(result.current.getBalanceForDay(21)).toBeUndefined()
  })

  it("sans données : aucun événement ni solde", () => {
    serve()
    const { result } = renderHook(() => useCalendarData(), { wrapper })

    expect(result.current.getEventsForDay(20)).toEqual([])
    expect(result.current.getBalanceForDay(20)).toBeNull()
    expect(result.current.selectedDayEvents).toEqual([])
  })

  it("mois suivant et précédent (changement d'année compris), un chargement par mois", async () => {
    const queries = serve()
    const { result } = renderHook(() => useCalendarData(), { wrapper })
    await loaded(result)

    act(() => result.current.setDate(new Date(2026, 11, 1)))
    act(() => result.current.nextMonth())
    await waitFor(() => expect(queries).toContain("?month=1&year=2027"))
    expect(result.current.month).toBe(1)

    act(() => result.current.prevMonth())
    act(() => result.current.prevMonth())
    await waitFor(() => expect(queries).toContain("?month=11&year=2026"))
    // 1er janvier = vendredi mais ici novembre 2026 démarre un dimanche → 6 cases vides
    expect(result.current.startingDay).toBe(6)
  })

  it("filtrer par compte relance le chargement avec account_id", async () => {
    const queries = serve()
    const { result } = renderHook(() => useCalendarData(), { wrapper })
    await loaded(result)

    act(() => result.current.setSelectedAccountId("4"))

    await waitFor(() => expect(queries).toContain("?month=6&year=2026&account_id=4"))
  })

  it("cliquer un jour l'ouvre et expose ses événements", async () => {
    serve()
    const { result } = renderHook(() => useCalendarData(), { wrapper })
    await loaded(result)

    act(() => result.current.handleDayClick(20))

    expect(result.current.selectedDay).toBe("2026-06-20")
    expect(result.current.isDayDetailOpen).toBe(true)
    expect(result.current.selectedDayEvents.map((e) => e.name)).toEqual(["Loyer"])
  })

  it("échec du calendrier : drapeau, toast, données vidées ; rechargement via reloadToken", async () => {
    let failing = true
    server.use(
      http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
      http.get(apiUrl("/analytics/calendar"), () => (failing ? new HttpResponse(null, { status: 500 }) : HttpResponse.json(calendar()))),
    )
    const { result } = renderHook(() => useCalendarData(), { wrapper })

    await waitFor(() => expect(result.current.loadFailed).toBe(true))
    expect(await screen.findByText("Impossible de charger le calendrier")).toBeInTheDocument()
    expect(result.current.data).toBeNull()
    expect(result.current.loading).toBe(false)

    failing = false
    act(() => result.current.setReloadToken((n) => n + 1))
    await loaded(result)
    expect(result.current.loadFailed).toBe(false)
  })

  it("échec du chargement des comptes : toast, liste vide", async () => {
    server.use(
      http.get(apiUrl("/accounts"), () => new HttpResponse(null, { status: 500 })),
      http.get(apiUrl("/analytics/calendar"), () => HttpResponse.json(calendar())),
    )
    const { result } = renderHook(() => useCalendarData(), { wrapper })

    expect(await screen.findByText("Impossible de charger les comptes")).toBeInTheDocument()
    expect(result.current.accounts).toEqual([])
  })
})

describe("useCalendarData : valider une échéance d'investissement", () => {
  const recurring = { id: 7, account_id: 1, name: "DCA", note: null, ticker: "CW8", asset_class: "etf", quantity: 2, unit_price: 100 }

  it("sur un compte titres, une sortie devient un versement d'investissement", async () => {
    const posted: unknown[] = []
    serve({ accounts: [makeAccount({ id: 1, type: "investissement" })] })
    server.use(
      http.get(apiUrl("/recurring-transactions/"), () => HttpResponse.json([recurring])),
      http.post(apiUrl("/investment-transactions"), async ({ request }) => { posted.push(await request.json()); return HttpResponse.json({ id: 1 }) }),
    )
    const { result } = renderHook(() => useCalendarData(), { wrapper })
    await waitFor(() => expect(result.current.accounts).toHaveLength(1))
    act(() => result.current.setSelectedDay("2026-06-20"))

    await act(() => result.current.handleValidate(event({ type: "Sortie" })))

    expect(posted).toEqual([expect.objectContaining({ account_id: 1, type: "versement", amount: 850, note: "DCA", ticker: "CW8", quantity: 2 })])
    expect(await screen.findByText("Transaction validée !")).toBeInTheDocument()
  })

  it("entrée ou vente sur un compte titres → retrait", async () => {
    const posted: { type: string }[] = []
    serve({ accounts: [makeAccount({ id: 1, type: "assurance_vie" })] })
    server.use(
      http.get(apiUrl("/recurring-transactions/"), () => HttpResponse.json([recurring])),
      http.post(apiUrl("/investment-transactions"), async ({ request }) => { posted.push((await request.json()) as { type: string }); return HttpResponse.json({ id: 1 }) }),
    )
    const { result } = renderHook(() => useCalendarData(), { wrapper })
    await waitFor(() => expect(result.current.accounts).toHaveLength(1))
    act(() => result.current.setSelectedDay("2026-06-20"))

    await act(() => result.current.handleValidate(event({ type: "Entree" })))
    await act(() => result.current.handleValidate(event({ type: "vente" })))

    expect(posted.map((p) => p.type)).toEqual(["retrait", "retrait"])
  })

  it("récurrence introuvable : toast, aucune écriture", async () => {
    serve()
    const writes: string[] = []
    server.use(
      http.get(apiUrl("/recurring-transactions/"), () => HttpResponse.json([])),
      http.post(apiUrl("/transactions"), () => { writes.push("tx"); return HttpResponse.json({}) }),
    )
    const { result } = renderHook(() => useCalendarData(), { wrapper })
    await waitFor(() => expect(result.current.accounts).toHaveLength(1))
    act(() => result.current.setSelectedDay("2026-06-20"))

    await act(() => result.current.handleValidate(event()))

    expect(await screen.findByText("Compte non trouvé")).toBeInTheDocument()
    expect(writes).toEqual([])
  })

  it("sans récurrence liée ou sans jour sélectionné : ne fait rien", async () => {
    serve()
    const { result } = renderHook(() => useCalendarData(), { wrapper })
    await waitFor(() => expect(result.current.accounts).toHaveLength(1))

    await act(() => result.current.handleValidate(event()))  // pas de jour sélectionné
    act(() => result.current.setSelectedDay("2026-06-20"))
    await act(() => result.current.handleValidate(event({ recurring_id: undefined })))

    expect(screen.queryByText(/Compte non trouvé|Transaction validée/)).not.toBeInTheDocument()
  })

  it("échec de l'écriture : toast d'erreur", async () => {
    serve()
    server.use(
      http.get(apiUrl("/recurring-transactions/"), () => HttpResponse.json([{ id: 7, account_id: 1, name: "Loyer" }])),
      http.post(apiUrl("/transactions"), () => new HttpResponse(null, { status: 500 })),
    )
    const { result } = renderHook(() => useCalendarData(), { wrapper })
    await waitFor(() => expect(result.current.accounts).toHaveLength(1))
    act(() => result.current.setSelectedDay("2026-06-20"))

    await act(() => result.current.handleValidate(event()))

    expect(await screen.findByText("Erreur lors de la validation")).toBeInTheDocument()
  })
})
