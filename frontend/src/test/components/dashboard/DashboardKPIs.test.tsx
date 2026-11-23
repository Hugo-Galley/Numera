/** KPI du tableau de bord : « Solde du mois » (revenus − dépenses, `solde_du_mois` de l'API), « à date » tant que le mois n'est pas fini, et montant mis de côté. */
import { screen } from "@testing-library/react"
import { DashboardKPIs } from "@/components/dashboard/DashboardKPIs"
import type { BudgetOverview } from "@/components/dashboard/types"
import { partial } from "@/test/support/factories"
import { renderWithProviders } from "@/test/support/render"

const analytics = partial<BudgetOverview>({
  revenus_totaux: 0, depenses_reelles: 1840.28, depenses_totales: 1840.28,
  solde_du_mois: -1840.28, mis_de_cote: 300, epargne_realisee: 999999, solde_actuel: 38413,
})

describe("DashboardKPIs", () => {
  it("mois en cours, tous les comptes : « Solde du mois à date », position dans le mois et mis de côté", () => {
    renderWithProviders(<DashboardKPIs selectedAccountId="all" displayCurrency="EUR" analytics={analytics} kpiHistory={[]} progress={{ day: 23, total: 30 }} />)

    expect(screen.getByText("Solde du mois à date")).toBeInTheDocument()
    expect(screen.getByText(/-1\s840,28/)).toBeInTheDocument()
    expect(screen.queryByText(/999\s999/)).not.toBeInTheDocument()
    expect(screen.getByText(/À date \(J23\/30\)/)).toHaveTextContent(/Mis de côté : 300,00/)
  })

  it("mois terminé : « Solde du mois », plus d'« Épargne réalisée »", () => {
    renderWithProviders(<DashboardKPIs selectedAccountId="all" displayCurrency="EUR" analytics={analytics} kpiHistory={[]} />)

    expect(screen.getByText("Solde du mois")).toBeInTheDocument()
    expect(screen.getByText(/Mis de côté : 300,00/)).toBeInTheDocument()
    expect(screen.queryByText(/Épargne/i)).not.toBeInTheDocument()
  })

  it("un compte choisi : « Solde Actuel », même en cours de mois", () => {
    renderWithProviders(<DashboardKPIs selectedAccountId="3" displayCurrency="EUR" analytics={analytics} kpiHistory={[]} progress={{ day: 23, total: 30 }} />)

    expect(screen.getByText("Solde Actuel")).toBeInTheDocument()
    expect(screen.queryByText(/Mis de côté/)).not.toBeInTheDocument()
  })
})
