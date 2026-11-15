/** Page Investissements : comptes détenus pour un tiers, affichés à part et hors totaux. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { ThirdPartyAccounts } from "@/pages/Investments/ThirdPartyAccounts"

const overview = (third_party_accounts: unknown[]) =>
  server.use(http.get(apiUrl("/analytics/portfolio"), () => HttpResponse.json({ accounts: [], third_party_accounts })))

describe("Investissements : comptes détenus pour un tiers", () => {
  it("affiche chaque compte avec son bénéficiaire, sa valeur et sa plus-value", async () => {
    overview([{ account_id: 7, account_name: "AXA Shareplan Maman", held_for: "Maman", value_eur: 1200, unrealized_eur: 400, unrealized_pct: 50 }])
    renderWithProviders(<ThirdPartyAccounts />, { route: "/investments", auth: true })

    expect(await screen.findByText("Détenu pour un tiers")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /AXA Shareplan Maman/ })).toHaveAttribute("href", "/accounts/7")
    expect(screen.getByText("Pour Maman")).toBeInTheDocument()
    expect(screen.getByText(/1\s?200,00/)).toBeInTheDocument()
    expect(screen.getByText(/\+\s?400,00/)).toBeInTheDocument()
  })

  it("aucun compte pour un tiers : rien n'est affiché", async () => {
    overview([])
    const { container } = renderWithProviders(<ThirdPartyAccounts />, { route: "/investments", auth: true })

    await new Promise((r) => setTimeout(r, 50))
    expect(container.querySelector("[data-testid='third-party-accounts']")).toBeNull()
    expect(screen.queryByText("Détenu pour un tiers")).not.toBeInTheDocument()
  })
})
