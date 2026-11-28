/** Page Investissements : carte « Pire baisse » (chiffres calculés par le backend). */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { DrawdownCard } from "@/pages/Investments/DrawdownCard"

const overview = (drawdown: unknown) =>
  server.use(http.get(apiUrl("/analytics/portfolio"), () => HttpResponse.json({ accounts: [], third_party_accounts: [], drawdown })))

describe("Investissements : pire baisse", () => {
  it("affiche la baisse, le sommet, le creux et la baisse actuelle", async () => {
    overview({ max_drawdown_pct: -20, peak_date: "2026-03-02", trough_date: "2026-05-04", recovery_date: null, current_drawdown_pct: -10 })
    renderWithProviders(<DrawdownCard />, { route: "/investments", auth: true })

    expect(await screen.findByRole("heading", { name: "Pire baisse" })).toBeInTheDocument()
    expect(screen.getByText(/-20,0/)).toBeInTheDocument()
    expect(screen.getByText("02/03/2026 → 04/05/2026")).toBeInTheDocument()
    expect(screen.getByText("Sommet pas encore retrouvé")).toBeInTheDocument()
    expect(screen.getByText(/-10,0/)).toBeInTheDocument()
  })

  it("sans historique : la carte reste et dit pourquoi il n'y a pas de chiffre", async () => {
    overview(null)
    renderWithProviders(<DrawdownCard />, { route: "/investments", auth: true })

    expect(await screen.findByText(/Pas encore assez d'historique/)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Pire baisse" })).toBeInTheDocument()
  })

  it("chargement en échec : message d'erreur et nouvel essai, jamais une carte vide", async () => {
    server.use(http.get(apiUrl("/analytics/portfolio"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))
    const { user } = renderWithProviders(<DrawdownCard />, { route: "/investments", auth: true })

    expect(await screen.findByRole("alert")).toBeInTheDocument()
    overview({ max_drawdown_pct: -5, peak_date: "2026-03-02", trough_date: "2026-03-10", recovery_date: "2026-04-01", current_drawdown_pct: 0 })
    await user.click(screen.getByRole("button", { name: "Réessayer" }))
    expect(await screen.findByText("Au plus haut")).toBeInTheDocument()
  })
})
