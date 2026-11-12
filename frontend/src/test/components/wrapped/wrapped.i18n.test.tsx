/** Bilan annuel et Outils en anglais : diapositives, variations, libellés lus à l'affichage. */
import { render } from "@testing-library/react"
import { setLanguage } from "@/i18n"
import type { WrappedReport } from "@/types/wrapped"
import { TYPE_LABELS } from "@/components/tools/WealthForecast/types"
import { Delta, hoursLabel, monthName } from "@/components/wrapped/format"
import { buildSlides } from "@/components/wrapped/wrappedSlides"

const report: WrappedReport = {
  year: 2025, available_years: [2025], has_data: true, is_partial: true, months_covered: 6,
  totals: { income: 30000, real_expenses: 18000, saved: 12000, savings_rate: 40, invested: 5000, dividends: 100, net_worth_start: 10000, net_worth_end: 22000, net_worth_change: 12000, subscriptions_cost: 300, expense_count: 120 },
  months: [{ month: 1, income: 5000, real_expenses: 3000, saved: 2000 }],
  most_expensive_month: { month: 1, income: 5000, real_expenses: 3000, saved: 2000 },
  thriftiest_month: { month: 2, income: 5000, real_expenses: 2000, saved: 3000 },
  top_categories: [{ name: "Courses", icon: null, color: null, total: 900, percentage: 30, work_hours: null }],
  top_merchants: [], biggest_expense: { merchant: "Garage", amount: 800, date: "2025-03-04", category: null, work_hours: null },
  hourly_rate: null, real_expenses_work_hours: null, net_worth_change_pct: 120,
  new_subscriptions: [], stopped_subscriptions: [{ name: "Vieux service", monthly_cost: 10 }], stopped_subscriptions_yearly_saving: 120, previous: null,
}

function slidesText() {
  return buildSlides(report, 7).map((s) => render(<div>{s.content}</div>).container.textContent).join(" | ")
}

describe("bilan annuel et outils en anglais", () => {
  afterEach(() => setLanguage("fr"))

  it("diapositives en français", () => {
    const text = slidesText()
    expect(text).toContain("de janvier à juin")
    expect(text).toContain("Ton plus gros poste")
    expect(text).toContain("40 %")
  })

  it("diapositives en anglais, formats compris", async () => {
    await setLanguage("en")
    const text = slidesText()
    expect(text).toContain("from January to June")
    expect(text).toContain("Your biggest category")
    expect(text).toContain("Your lowest-spending month".replace("Your ", "your "))
    expect(text).toContain("40%")
    expect(text).toContain("More in the next recap.")
    expect(text).not.toMatch(/Ton |Tes |dépenses|économisés/)
  })

  it("variation, durée de travail et mois suivent la langue", async () => {
    await setLanguage("en")
    expect(monthName(7)).toBe("July")
    expect(hoursLabel(14, 7)).toMatch(/of work/)
    const { container } = render(<Delta value={12.5} vsYear={2024} />)
    expect(container.textContent).toContain("+12.5%")
    expect(container.textContent).toContain("vs 2024")
  })

  it("libellés de groupes de comptes calculés à la lecture", async () => {
    expect(TYPE_LABELS.autres).toBe("Courant et épargne")
    await setLanguage("en")
    expect(TYPE_LABELS.autres).toBe("Checking and savings")
  })
})
