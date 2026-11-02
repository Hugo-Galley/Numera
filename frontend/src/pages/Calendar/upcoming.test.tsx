/** Calendrier : les saisies réelles datées dans le futur sont des échéances à venir, distinctes des récurrences prévues. */
import { render, screen, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import type { CalendarEvent } from "./types"
import type { CalendarCtx } from "./useCalendar"
import { CalendarSummary } from "./CalendarSummary"
import { DayDetailDialog } from "./DayDetailDialog"

const event = (over: Partial<CalendarEvent>): CalendarEvent => ({
  id: "tx_1", date: "2026-06-20T00:00:00", name: "Loyer", amount: 850, type: "Sortie", category_id: null,
  is_projected: false, is_upcoming: false, currency: "EUR", ...over,
})

const ctxWith = (events: CalendarEvent[]) => ({
  data: { month: 6, year: 2026, events, daily_balances: [] },
  date: new Date(2026, 5, 10), embedded: false, isPrivacyMode: false, month: 6, year: 2026,
  isDayDetailOpen: true, selectedDay: "2026-06-20", selectedDayEvents: events, setIsDayDetailOpen: () => undefined,
  getBalanceForDay: () => null, handleValidate: () => undefined, validating: null,
}) as unknown as CalendarCtx

describe("Calendrier : transactions à venir", () => {
  it("liste une saisie future dans les prochaines échéances, pas une transaction passée", () => {
    render(<MemoryRouter><CalendarSummary ctx={ctxWith([
      event({ id: "tx_1", name: "Loyer", is_upcoming: true }),
      event({ id: "tx_2", name: "Courses", date: "2026-06-02T00:00:00" }),
    ])} /></MemoryRouter>)

    const card = screen.getByText("Prochaines Échéances").closest("div[class*='border']")!.parentElement!
    expect(within(card).getByText("Loyer")).toBeInTheDocument()
    expect(within(card).queryByText("Courses")).not.toBeInTheDocument()
  })

  it("le détail du jour marque une saisie future « À VENIR » et une récurrence « PRÉVU »", () => {
    render(<DayDetailDialog ctx={ctxWith([
      event({ id: "tx_1", name: "Loyer", is_upcoming: true }),
      event({ id: "proj_1", name: "Netflix", is_projected: true, is_upcoming: true, recurring_id: 3 }),
      event({ id: "tx_2", name: "Courses" }),
    ])} />)

    const rent = screen.getByText("Loyer").closest("div.rounded-lg")! as HTMLElement
    expect(within(rent).getByText("À VENIR")).toBeInTheDocument()
    expect(within(rent).queryByText("PRÉVU")).not.toBeInTheDocument()
    const netflix = screen.getByText("Netflix").closest("div.rounded-lg")! as HTMLElement
    expect(within(netflix).getByText("PRÉVU")).toBeInTheDocument()
    expect(within(netflix).queryByText("À VENIR")).not.toBeInTheDocument()
    const groceries = screen.getByText("Courses").closest("div.rounded-lg")! as HTMLElement
    expect(within(groceries).queryByText("À VENIR")).not.toBeInTheDocument()
  })
})
