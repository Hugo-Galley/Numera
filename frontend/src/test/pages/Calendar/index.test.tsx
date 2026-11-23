/** Calendrier : le montant sous chaque jour dit ce qu'il est (solde fin de journée) et sa portée en « Tous les comptes ». */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { resetApiCache } from "@/lib/apiCache"
import type { CalendarData } from "@/pages/Calendar/types"
import Calendar from "@/pages/Calendar"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

const ev = (id: string, name: string, type: string, is_projected: boolean, is_upcoming = false) => ({
  id, date: "2026-06-20T00:00:00", name, amount: 10, type, category_id: null, is_projected, is_upcoming, currency: "EUR", recurring_id: null,
})
const calendar = {
  month: 6, year: 2026,
  events: [ev("a", "Loyer", "Sortie", true), ev("b", "Salaire", "Entree", false), ev("c", "Box", "Sortie", false, true), ev("d", "Gym", "Sortie", false)],
  daily_balances: [{ date: "2026-06-20", balance: 1234 }, { date: "2026-06-21", balance: -5 }],
} as unknown as CalendarData

beforeEach(() => {
  resetApiCache()
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date(2026, 5, 15))
  server.use(
    http.get(apiUrl("/accounts"), () => HttpResponse.json([makeAccount({ id: 1, name: "Courant" })])),
    http.get(apiUrl("/analytics/calendar"), () => HttpResponse.json(calendar)),
  )
})
afterEach(() => vi.useRealTimers())

describe("Calendrier : solde affiché", () => {
  it("légende : solde estimé en fin de journée, somme de tous les comptes en vue globale", async () => {
    renderWithProviders(<Calendar embedded />, { auth: true })

    expect(await screen.findByText(/solde estimé en fin de journée/)).toHaveTextContent(/somme de tous tes comptes actifs/)
  })

  it("le montant d'un jour porte son libellé « Solde fin de journée »", async () => {
    renderWithProviders(<Calendar embedded />, { auth: true })

    const amount = await screen.findByText(/1\s234,00/)
    expect(amount).toHaveAttribute("title", expect.stringMatching(/^Solde fin de journée : 1\s234,00/))
  })

  it("événements du jour listés (3 au plus, puis « + n autres ») et solde négatif signalé", async () => {
    renderWithProviders(<Calendar embedded />, { auth: true })

    expect((await screen.findAllByText("Loyer")).length).toBeGreaterThan(0)
    expect(screen.getAllByText("Salaire").length).toBeGreaterThan(0)
    expect(screen.getByText(/\+ 1 autres/)).toBeInTheDocument()
    expect(screen.getByText(/-5,00/).className).toMatch(/text-red-500/)
  })
})
