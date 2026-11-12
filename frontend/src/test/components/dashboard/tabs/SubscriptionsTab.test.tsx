/** Onglet Abonnements : le coût mensuel affiché est celui du backend (audit F-02), pas une somme faite ici. */
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { SubscriptionsTab } from "@/components/dashboard/tabs/SubscriptionsTab"

vi.mock("@/components/ui/work-hours", () => ({ WorkHours: () => null }))

const sub = (name: string, monthly_cost: number, status: string) => ({
  name, category_name: "Abonnement", monthly_cost, annual_cost: monthly_cost * 12, status, amount: monthly_cost,
  frequency: "monthly", is_recurring_entity: status !== "potential", counts_in_total: status === "active",
})

describe("SubscriptionsTab", () => {
  it("affiche total_monthly du backend plutôt que la somme des lignes", () => {
    const data = { subscriptions: [sub("Netflix", 10, "active"), sub("Spotify", 5, "potential")], total_monthly: 12.34, total_annual: 148.08, price_changes: [] }
    render(<MemoryRouter><SubscriptionsTab subscriptions={data} displayCurrency="EUR" /></MemoryRouter>)
    expect(screen.getByText(/12,34/)).toBeInTheDocument()
    expect(screen.queryByText(/15,00/)).not.toBeInTheDocument()
  })
})
