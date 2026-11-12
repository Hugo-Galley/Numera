/** Onglet Projections : solde projeté, point bas, prochains flux et analyse de trésorerie (chiffres du backend). */
import { screen } from "@testing-library/react"
import { renderWithProviders } from "@/test/support/render"
import { ProjectionsTab } from "@/components/dashboard/tabs/ProjectionsTab"

const event = (name: string, amount: number, is_income: boolean, date: string) => ({ name, amount, is_income, date })
const projection = {
  current_balance: 1000, projected_balance: 1450, low_point: 300, low_point_date: "2026-07-03T00:00:00",
  points: [{ date: "2026-07-01T00:00:00", balance: 1000 }, { date: "2026-07-03T00:00:00", balance: 300 }],
  events: [event("Salaire", 2000, true, "2026-07-01T00:00:00"), event("Loyer", 750, false, "2026-07-05T00:00:00")],
}

describe("ProjectionsTab", () => {
  it("affiche le solde projeté avec l'écart signé, le point bas daté et le nombre de flux attendus", () => {
    renderWithProviders(<ProjectionsTab projection={projection} displayCurrency="EUR" />, { auth: true })

    expect(screen.getByText("Solde Projeté (60j)")).toBeInTheDocument()
    expect(screen.getByText(/1\s450,00/)).toBeInTheDocument()
    expect(screen.getByText(/\+450,00/)).toBeInTheDocument()
    // Le point bas figure dans la carte et dans la phrase d'analyse
    expect(screen.getAllByText(/300,00/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Prévu le 3 juillet/)).toBeInTheDocument()
    expect(screen.getByText("2")).toBeInTheDocument()
  })

  it("liste les prochains flux : revenus en « + », dépenses en « - »", () => {
    renderWithProviders(<ProjectionsTab projection={projection} displayCurrency="EUR" />, { auth: true })

    expect(screen.getByText("Salaire")).toBeInTheDocument()
    expect(screen.getByText(/\+2\s000,00/)).toBeInTheDocument()
    expect(screen.getByText("Loyer")).toBeInTheDocument()
    expect(screen.getByText(/-750,00/)).toBeInTheDocument()
  })

  it("point bas positif : analyse « reste positif » et conseil d'épargne si le solde progresse", () => {
    renderWithProviders(<ProjectionsTab projection={projection} displayCurrency="EUR" />, { auth: true })

    expect(screen.getByText(/devrait rester/)).toBeInTheDocument()
    expect(screen.getByText("Conseil")).toBeInTheDocument()
    expect(screen.getByText(/excédent de trésorerie prévu/)).toBeInTheDocument()
  })

  it("point bas négatif et solde en baisse : analyse « sous zéro », pas de conseil, écart sans signe +", () => {
    renderWithProviders(
      <ProjectionsTab projection={{ ...projection, projected_balance: 800, low_point: -150 }} displayCurrency="EUR" />,
      { auth: true },
    )

    expect(screen.getByText(/sous zéro/)).toBeInTheDocument()
    expect(screen.queryByText("Conseil")).not.toBeInTheDocument()
    expect(screen.queryByText(/\+200,00/)).not.toBeInTheDocument()
    expect(screen.getByText(/-200,00/)).toBeInTheDocument()
  })

  it("aucune projection : valeurs à zéro, date « - », aucun flux, sans erreur", () => {
    renderWithProviders(<ProjectionsTab projection={null} displayCurrency="EUR" />, { auth: true })

    expect(screen.getByText(/Prévu le -/)).toBeInTheDocument()
    expect(screen.getByText("0")).toBeInTheDocument()
    expect(screen.queryByText("Salaire")).not.toBeInTheDocument()
  })

  it("devise d'affichage : les montants suivent la devise demandée", () => {
    renderWithProviders(<ProjectionsTab projection={projection} displayCurrency="USD" />, { auth: true })

    expect(screen.getAllByText(/\$/).length).toBeGreaterThan(0)
  })
})
