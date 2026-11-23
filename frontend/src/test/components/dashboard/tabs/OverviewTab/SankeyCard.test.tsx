/** Carte « Flux financiers » : message quand le salaire n'est pas encore arrivé (la source « Déficit » n'en est pas un). */
import { screen } from "@testing-library/react"
import { SankeyCard } from "@/components/dashboard/tabs/OverviewTab/SankeyCard"
import { useOverviewTab } from "@/components/dashboard/tabs/OverviewTab/useOverviewTab"
import { renderWithProviders } from "@/test/support/render"

function Card({ incomePending }: { incomePending: boolean }) {
  const ctx = useOverviewTab({ nodes: [], links: [] }, [], "EUR", [], null, { month: 11, year: 2026, accountId: null })
  return <SankeyCard ctx={ctx} incomePending={incomePending} />
}

describe("SankeyCard", () => {
  it("mois en cours sans revenu : explique que ce n'est pas un déficit", () => {
    renderWithProviders(<Card incomePending />, { auth: true })

    expect(screen.getByText(/Aucun revenu n'est encore arrivé ce mois-ci/)).toHaveTextContent("Ce n'est pas un déficit du mois.")
  })

  it("sinon : pas de message", () => {
    renderWithProviders(<Card incomePending={false} />, { auth: true })

    expect(screen.queryByText(/Aucun revenu n'est encore arrivé/)).not.toBeInTheDocument()
  })
})
