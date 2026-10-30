import type { ReactNode } from "react"
import { act, renderHook, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { makeAccount } from "@/test/factories"
import { server } from "@/test/server"
import { UIProvider } from "@/providers/UIProvider"
import type { CalendarEvent } from "./types"
import { useCalendarData } from "./useCalendarData"

const wrapper = ({ children }: { children: ReactNode }) => <UIProvider>{children}</UIProvider>

const EVENT: CalendarEvent = {
  id: "r-7-2026-06-20",
  date: "2026-06-20T00:00:00",
  name: "Loyer",
  amount: 850,
  type: "Sortie",
  category_id: 3,
  is_projected: true,
  currency: "EUR",
  recurring_id: 7,
}

describe("useCalendarData : valider une échéance", () => {
  it("crée la transaction à partir de la récurrence retrouvée dans la liste", async () => {
    const posted: unknown[] = []
    server.use(
      http.get(apiUrl("/accounts"), () => HttpResponse.json([makeAccount({ id: 1 })])),
      http.get(apiUrl("/analytics/calendar"), () => HttpResponse.json({ month: 6, year: 2026, events: [], daily_balances: [] })),
      http.get(apiUrl("/recurring-transactions/"), () =>
        HttpResponse.json([
          { id: 3, account_id: 99, name: "Autre" },
          { id: 7, account_id: 1, name: "Loyer" },
        ]),
      ),
      http.post(apiUrl("/transactions"), async ({ request }) => {
        posted.push(await request.json())
        return HttpResponse.json({ id: 1 })
      }),
    )

    const { result } = renderHook(() => useCalendarData({ embedded: false }), { wrapper })
    await waitFor(() => expect(result.current.accounts).toHaveLength(1))
    act(() => result.current.setSelectedDay("2026-06-20"))
    await act(async () => {
      await result.current.handleValidate(EVENT)
    })

    expect(posted).toEqual([
      expect.objectContaining({ account_id: 1, type: "Sortie", merchant: "Loyer", amount: 850, recurring_transaction_id: 7 }),
    ])
  })
})
