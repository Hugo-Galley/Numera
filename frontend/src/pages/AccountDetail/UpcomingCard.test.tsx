/** Carte « À venir » du compte : saisies futures et échéances récurrentes, solde projeté. */
import { screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { UpcomingCard } from "./UpcomingCard"

const event = (over: Record<string, unknown>) => ({
  date: "2026-03-20T00:00:00", name: "Loyer", amount: 200, type: "scheduled", is_income: false,
  transaction_id: 7, possible_duplicate: false, ...over,
})

function serveProjection(events: ReturnType<typeof event>[], current = 1400, projected = 1185) {
  server.use(http.get(apiUrl("/analytics/cashflow-projection"), () =>
    HttpResponse.json({ points: [], events, current_balance: current, projected_balance: projected, low_point: projected, low_point_date: "2026-03-20" })))
}

describe("UpcomingCard", () => {
  it("liste les saisies et échéances à venir avec le solde projeté", async () => {
    serveProjection([
      event({}),
      event({ date: "2026-03-15T00:00:00", name: "Netflix", amount: 15, type: "recurring", transaction_id: null }),
    ])
    renderWithProviders(<UpcomingCard accountId={1} currency="EUR" refreshKey={0} />, { auth: true })

    const card = await screen.findByRole("region", { name: "À venir" })
    expect(within(card).getByText(/1\s?185,00/)).toBeInTheDocument()
    expect(screen.queryByText("Loyer")).not.toBeInTheDocument()

    await userEvent.click(within(card).getByRole("button", { name: /À venir/ }))
    const dialog = await screen.findByRole("dialog") // popover Radix
    expect(within(dialog).getByText("Loyer")).toBeInTheDocument()
    expect(within(dialog).getByText("Netflix")).toBeInTheDocument()
    expect(within(dialog).getByText("Récurrent")).toBeInTheDocument()
    expect(within(dialog).getByText(/Solde projeté/)).toBeInTheDocument()
  })

  it("demande la projection du compte sur 30 jours", async () => {
    const searches: string[] = []
    server.use(http.get(apiUrl("/analytics/cashflow-projection"), ({ request }) => {
      searches.push(new URL(request.url).search)
      return HttpResponse.json({ points: [], events: [], current_balance: 0, projected_balance: 0, low_point: 0, low_point_date: null })
    }))
    renderWithProviders(<UpcomingCard accountId={4} currency="EUR" refreshKey={0} />, { auth: true })

    await vi.waitFor(() => expect(searches).toEqual(["?days=30&account_id=4"]))
  })

  it("signale un doublon possible entre une saisie et une récurrence", async () => {
    serveProjection([
      event({ name: "Netflix", amount: 15, possible_duplicate: true }),
      event({ name: "Netflix", amount: 15, type: "recurring", transaction_id: null, possible_duplicate: true }),
    ])
    renderWithProviders(<UpcomingCard accountId={1} currency="EUR" refreshKey={0} />, { auth: true })

    await userEvent.click(await screen.findByRole("button", { name: /À venir/ }))
    expect(await screen.findAllByText("Doublon possible")).toHaveLength(2)
  })

  it("ne s'affiche pas quand rien n'est prévu", async () => {
    serveProjection([])
    renderWithProviders(<UpcomingCard accountId={1} currency="EUR" refreshKey={0} />, { auth: true })

    await vi.waitFor(() => expect(screen.queryByRole("region", { name: "À venir" })).not.toBeInTheDocument())
  })
})
