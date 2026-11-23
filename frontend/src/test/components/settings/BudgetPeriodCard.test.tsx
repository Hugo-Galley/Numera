import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { BudgetPeriodCard } from "@/components/settings/BudgetPeriodCard"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

const PERIOD = { mode: "civil", start: "2026-11-01", end: "2026-12-01" }

describe("BudgetPeriodCard", () => {
  it("l'interrupteur porte un nom accessible et bascule en mois de paie", async () => {
    const puts: unknown[] = []
    server.use(
      http.get(apiUrl("/analytics/budget-period"), () => HttpResponse.json(PERIOD)),
      http.put(apiUrl("/analytics/budget-period"), async ({ request }) => {
        puts.push(await request.json())
        return HttpResponse.json({ ...PERIOD, mode: "salary" })
      }),
    )
    const { user } = renderWithProviders(<BudgetPeriodCard />, { auth: true })

    const toggle = await screen.findByRole("switch", { name: "Mois de paie" })
    await waitFor(() => expect(toggle).toBeEnabled())
    await user.click(toggle)

    await waitFor(() => expect(puts).toEqual([{ mode: "salary" }]))
    expect(await screen.findByText("Mois de paie activé")).toBeInTheDocument()
  })
})
