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

const calendar: CalendarData = { month: 6, year: 2026, events: [], daily_balances: [{ date: "2026-06-20", balance: 1234 }] }

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
})
