/** Onglets du tableau de bord : textes, pluriels, balises (<Trans>) et formats en anglais comme en français. */
import { screen } from "@testing-library/react"
import { setLanguage } from "@/i18n"
import { renderWithProviders } from "@/test/support/render"
import { formatWorkDuration } from "@/components/ui/work-hours"
import { BudgetsTab } from "@/components/dashboard/tabs/BudgetsTab"
import { InsightsTab } from "@/components/dashboard/tabs/InsightsTab"
import { ProjectionsTab } from "@/components/dashboard/tabs/ProjectionsTab"
import { SubscriptionsTab } from "@/components/dashboard/tabs/SubscriptionsTab"
import { AccountVerificationBanner } from "@/components/dashboard/AccountVerificationBanner"
import { partial } from "@/test/support/factories"
import type { BudgetAlert, CashflowProjection, Insights, SubscriptionsData } from "@/components/dashboard/types"

// WorkHours lit WorkTimeProvider (non monté ici) ; formatWorkDuration reste réel
vi.mock("@/components/ui/work-hours", async (original) => ({ ...(await original<typeof import("@/components/ui/work-hours")>()), WorkHours: () => null }))

const scope = { month: 11, year: 2026, accountId: null }

describe("tableau de bord en anglais", () => {
  beforeEach(() => setLanguage("en"))
  afterEach(() => setLanguage("fr"))

  it("états vides des onglets", () => {
    renderWithProviders(
      <>
        <BudgetsTab budgetAlerts={[]} drilldownScope={scope} />
        <SubscriptionsTab subscriptions={partial<SubscriptionsData>({ subscriptions: [] })} displayCurrency="EUR" />
        <InsightsTab insights={partial<Insights>({ insights: [], health_score: { total_score: 80, metrics: [] } })} />
      </>,
    )
    expect(screen.getByText("Budget tracking")).toBeInTheDocument()
    expect(screen.getByText("No budget set up. Add limits in the category settings.")).toBeInTheDocument()
    expect(screen.getByText("No subscription detected.")).toBeInTheDocument()
    expect(screen.getByText("Financial Health")).toBeInTheDocument()
    expect(screen.getByText(/Everything looks under control/)).toBeInTheDocument()
  })

  it("budget : statut et libellés mensuel / annuel", () => {
    const alert = { category_id: 1, category_name: "Logement", monthly_ratio: 1.2, monthly_spent: 120, monthly_limit: 100, annual_ratio: 0.5, annual_spent: 600, annual_limit: 1200 }
    renderWithProviders(<BudgetsTab budgetAlerts={[partial<BudgetAlert>(alert)]} drilldownScope={scope} />)
    expect(screen.getByText("Over budget")).toBeInTheDocument()
    expect(screen.getByText(/^Monthly —/)).toBeInTheDocument()
    expect(screen.getByText(/^Yearly —/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Logement/ })).toHaveAttribute("title", "View transactions")
  })

  it("projections : phrases avec balises et montants au format anglais", () => {
    const projection = partial<CashflowProjection>({ projected_balance: 3000, current_balance: 2000, low_point: 1500, low_point_date: "2026-11-20", points: [], events: [] })
    renderWithProviders(<ProjectionsTab projection={projection} displayCurrency="EUR" />)
    expect(screen.getByText("Projected Balance (60d)")).toBeInTheDocument()
    expect(screen.getByText("positive")).toBeInTheDocument()
    expect(screen.getByText("€1,500.00", { selector: "span.font-bold" })).toBeInTheDocument()
    expect(screen.getByText(/Expected on 20 November/)).toBeInTheDocument()
    expect(screen.getByText("€1,000.00", { selector: "span.font-bold" })).toBeInTheDocument()
  })

  it("projections : solde négatif", () => {
    const projection = partial<CashflowProjection>({ projected_balance: 100, current_balance: 500, low_point: -50, low_point_date: "2026-11-20", points: [], events: [] })
    renderWithProviders(<ProjectionsTab projection={projection} displayCurrency="EUR" />)
    expect(screen.getByText("below zero")).toBeInTheDocument()
  })

  it("bannière de vérification : pluriel", async () => {
    const stale = (id: number) => ({ id, name: `Compte ${id}`, type: "courant", last_verified_at: "2020-01-01", active: true })
    renderWithProviders(<AccountVerificationBanner accounts={[stale(1)]} onAccountVerified={() => {}} />)
    expect(screen.getByText("1 account to update")).toBeInTheDocument()
  })

  it("durées de travail abrégées en anglais", () => {
    expect(formatWorkDuration(0.5, 7)).toBe("30 min")
    expect(formatWorkDuration(20, 7)).toBe("2.9 d")
  })
})

describe("tableau de bord en français", () => {
  it("garde les mêmes écrans, avec accord au pluriel", () => {
    const stale = (id: number) => ({ id, name: `Compte ${id}`, type: "courant", last_verified_at: "2020-01-01", active: true })
    renderWithProviders(<AccountVerificationBanner accounts={[stale(1), stale(2)]} onAccountVerified={() => {}} />)
    expect(screen.getByText("2 comptes à mettre à jour")).toBeInTheDocument()
    expect(formatWorkDuration(20, 7)).toBe("2,9 j")
  })
})
