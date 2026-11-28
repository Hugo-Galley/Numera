/** Page Investissements : quatre onglets, l'onglet actif dans l'adresse, chaque bloc à un seul endroit. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import Investments from "@/pages/Investments"
import { apiUrl } from "@/test/support/handlers"
import { LocationDisplay } from "@/test/support/LocationDisplay"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

const allocation = {
  items: [{ account_id: 1, account_name: "PEA", current_value: 1000, percentage: 100, gain_eur: 100, performance_pct: 10, currency: "EUR" }],
  total_current_value: 1000, total_gain_eur: 100, total_performance_pct: 10,
}
const advanced = { by_asset_class: [{ name: "Actions", value: 1000, percentage: 100, items: [] }], by_sector: [], by_geographic_zone: [] }

function serve() {
  server.use(
    http.get(apiUrl("/analytics/investments-allocation"), () => HttpResponse.json(allocation)),
    http.get(apiUrl("/analytics/investments-allocation-advanced"), () => HttpResponse.json(advanced)),
    http.get(apiUrl("/analytics/portfolio"), () => HttpResponse.json({ accounts: [] })),
    http.get(apiUrl("/analytics/stock-picking-benchmark"), () => HttpResponse.json(null)),
  )
}

const render = (route = "/investments") =>
  renderWithProviders(<><Investments /><LocationDisplay /></>, { route, auth: true })

describe("Page Investissements", () => {
  it("s'ouvre sur la vue d'ensemble : comptes et classes d'actifs, sans doublon de secteurs", async () => {
    serve()
    render()

    expect(await screen.findByRole("tab", { name: "Vue d'ensemble", selected: true })).toBeInTheDocument()
    expect(screen.getByText("Répartition par compte")).toBeInTheDocument()
    expect(screen.getByText("Par classe d'actif")).toBeInTheDocument()
    expect(screen.queryByText("Par secteur")).not.toBeInTheDocument()
    expect(screen.queryByText("Performance détaillée")).not.toBeInTheDocument()
  })

  it("garde l'onglet choisi dans l'adresse", async () => {
    serve()
    const { user } = render()

    await user.click(await screen.findByRole("tab", { name: "Exposition" }))
    expect(screen.getByLabelText("adresse")).toHaveTextContent("/investments?tab=exposure")
    expect(screen.queryByText("Répartition par compte")).not.toBeInTheDocument()
  })

  it("ouvre directement l'onglet demandé", async () => {
    serve()
    render("/investments?tab=performance")
    expect(await screen.findByRole("tab", { name: "Performance", selected: true })).toBeInTheDocument()
  })

  it("onglet inconnu : vue d'ensemble, et pas d'onglet Fonds sans fonds décomposé", async () => {
    serve()
    render("/investments?tab=inconnu")
    expect(await screen.findByRole("tab", { name: "Vue d'ensemble", selected: true })).toBeInTheDocument()
    expect(screen.queryByRole("tab", { name: "Fonds" })).not.toBeInTheDocument()
  })
})
