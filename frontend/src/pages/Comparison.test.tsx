/** Comparaison : les sélecteurs d'année suivent la date du jour (audit F-01). */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { afterEach, beforeEach } from "vitest"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import Comparison from "./Comparison"

describe("Comparison", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] })
    vi.setSystemTime(new Date(2027, 0, 5))
    server.use(
      http.get(apiUrl("/analytics/budget"), () => HttpResponse.json({})),
      http.get(apiUrl("/analytics/expenses-by-category"), () => HttpResponse.json({ items: [] })),
    )
  })
  afterEach(() => vi.useRealTimers())

  it("affiche 2027 (période A) et 2026 (période B) en janvier 2027", async () => {
    renderWithProviders(<Comparison />)
    const triggers = await screen.findAllByRole("combobox")
    const labels = triggers.map((t) => t.textContent)
    expect(labels).toContain("2027")
    expect(labels).toContain("2026")
  })
})
