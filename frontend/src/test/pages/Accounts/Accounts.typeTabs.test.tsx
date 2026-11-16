/** Page Comptes : onglets par type (Tous, Courants, Épargne, Investissement avec l'assurance vie, Crédits). */
import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import Accounts from "@/pages/Accounts/index"

const row = (o: Partial<ReturnType<typeof makeAccount>> & { name: string; type: string }) => ({ ...makeAccount(), active: true, ...o })

function serve(accounts: ReturnType<typeof row>[]) {
  server.use(
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json({ asset_classes: [], sectors: [], geographic_zones: [] })),
    http.get(apiUrl("/accounts"), () => HttpResponse.json(accounts)),
  )
}
const view = () => renderWithProviders(<Accounts />, { route: "/accounts", auth: true })
const tableNames = () => within(screen.getByRole("table")).getAllByRole("row").slice(1).map((r) => r.textContent ?? "")

describe("page Comptes : onglets par type", () => {
  it("filtre la liste par type, l'assurance vie rangée avec l'investissement", async () => {
    serve([
      row({ id: 1, name: "Compte joint", type: "courant" }),
      row({ id: 2, name: "Livret A", type: "epargne" }),
      row({ id: 3, name: "PEA", type: "investissement" }),
      row({ id: 4, name: "Assurance vie", type: "assurance_vie" }),
    ])
    const { user } = view()
    await screen.findAllByText("Livret A")
    expect(tableNames()).toHaveLength(4)

    await user.click(screen.getByRole("tab", { name: /Investissement/ }))
    const names = tableNames()
    expect(names).toHaveLength(2)
    expect(names.join()).toMatch(/PEA/)
    expect(names.join()).toMatch(/Assurance vie/)

    await user.click(screen.getByRole("tab", { name: /Épargne/ }))
    expect(tableNames()).toHaveLength(1)

    await user.click(screen.getByRole("tab", { name: /Tous/ }))
    expect(tableNames()).toHaveLength(4)
  })

  it("pas d'onglet pour un type sans compte, ni d'onglets pour un seul type", async () => {
    serve([row({ id: 1, name: "Compte joint", type: "courant" }), row({ id: 2, name: "Livret A", type: "epargne" })])
    view()
    await screen.findAllByText("Livret A")
    expect(screen.getByRole("tab", { name: /Courants/ })).toBeInTheDocument()
    expect(screen.queryByRole("tab", { name: /Crédits/ })).not.toBeInTheDocument()
  })

  it("un seul type de compte : pas d'onglets", async () => {
    serve([row({ id: 1, name: "Compte joint", type: "courant" })])
    view()
    await screen.findAllByText("Compte joint")
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument()
  })
})
