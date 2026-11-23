/** KPI du tableau de bord : un mois en cours affiche un « solde du mois à date », pas une « épargne réalisée ». */
import { screen } from "@testing-library/react"
import { DashboardKPIs } from "@/components/dashboard/DashboardKPIs"
import type { BudgetOverview } from "@/components/dashboard/types"
import { partial } from "@/test/support/factories"
import { renderWithProviders } from "@/test/support/render"

const analytics = partial<BudgetOverview>({ revenus_totaux: 0, depenses_reelles: 1840.28, depenses_totales: 1840.28, epargne_realisee: -1840.28, solde_actuel: 38413 })

describe("DashboardKPIs", () => {
  it("mois en cours, tous les comptes : « Solde du mois à date » avec la position dans le mois", () => {
    renderWithProviders(<DashboardKPIs selectedAccountId="all" displayCurrency="EUR" analytics={analytics} kpiHistory={[]} progress={{ day: 23, total: 30 }} />)

    expect(screen.getByText("Solde du mois à date")).toBeInTheDocument()
    expect(screen.getByText("À date (J23/30)")).toBeInTheDocument()
    expect(screen.queryByText("Épargne Réalisée")).not.toBeInTheDocument()
  })

  it("mois terminé : « Épargne Réalisée »", () => {
    renderWithProviders(<DashboardKPIs selectedAccountId="all" displayCurrency="EUR" analytics={analytics} kpiHistory={[]} />)

    expect(screen.getByText("Épargne Réalisée")).toBeInTheDocument()
  })

  it("un compte choisi : « Solde Actuel », même en cours de mois", () => {
    renderWithProviders(<DashboardKPIs selectedAccountId="3" displayCurrency="EUR" analytics={analytics} kpiHistory={[]} progress={{ day: 23, total: 30 }} />)

    expect(screen.getByText("Solde Actuel")).toBeInTheDocument()
  })
})
