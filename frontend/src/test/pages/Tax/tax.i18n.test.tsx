/** Fiscalité et Audit en anglais : cartes d'enveloppes, libellés de type, constantes lues à l'affichage. */
import { screen } from "@testing-library/react"
import { setLanguage } from "@/i18n"
import { renderWithProviders } from "@/test/support/render"
import { severityLabel } from "@/pages/Audit/types"
import { KIND_LABELS, type WrapperCard } from "@/pages/Tax/types"
import { WrapperCardView } from "@/pages/Tax/TaxWidgets"

const card: WrapperCard = {
  kind: "assurance_vie", account_id: 4, account_name: "Assurance-vie", opened_at: "2018-05-01", current: 5000, ceiling: null, remaining: null,
  used_pct: null, age_years: 8.4, milestone_years: 8, milestone_reached: true, estimated_tax_saving: null, allowance: 4600, total_contributed: null,
  blocked: null, available: null, next_unlock_date: null, alerts: [],
}

describe("fiscalité et audit en anglais", () => {
  afterEach(() => setLanguage("fr"))

  it("libellés calculés à la lecture, pas figés à l'import", async () => {
    expect(KIND_LABELS.assurance_vie).toBe("Assurance-vie")
    expect(severityLabel.high).toBe("Priorité haute")
    await setLanguage("en")
    expect(KIND_LABELS.assurance_vie).toBe("Life insurance")
    expect(severityLabel.high).toBe("High priority")
    expect(severityLabel.low).toBe("Suggestion")
  })

  it("carte d'enveloppe : ancienneté et seuil atteint", async () => {
    await setLanguage("en")
    renderWithProviders(<WrapperCardView card={card} />)
    expect(screen.getByText(/Age: 8\.4 yr\(s\) \/ 8 yrs — reached/)).toBeInTheDocument()
    expect(screen.getByText("Life insurance")).toBeInTheDocument()
  })

  it("carte d'enveloppe en français", () => {
    renderWithProviders(<WrapperCardView card={card} />)
    expect(screen.getByText(/Ancienneté : 8,4 an\(s\) \/ 8 ans — atteint/)).toBeInTheDocument()
  })
})
