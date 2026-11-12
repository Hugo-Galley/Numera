/** Méthode de calcul de la prévision de patrimoine : volet repliable, saisies des hypothèses et valeurs affichées. */
import { screen, within } from "@testing-library/react"
import { vi } from "vitest"
import { partial } from "@/test/support/partial"
import { renderWithProviders } from "@/test/support/render"
import { ForecastMethodCard } from "@/components/tools/WealthForecast/ForecastMethodCard"
import type { Forecast } from "@/components/tools/WealthForecast/types"
import type { WealthForecastView } from "@/components/tools/WealthForecast/useWealthForecast"

const forecast: Forecast = {
  computed_monthly_savings: 420,
  observed_investment_return_pct: 6.5,
  savings_overridden: false,
  savings_months: [{ label: "mai 2026", revenus: 3000, depenses_reelles: 2500, epargne_flow: 500 }],
  return_breakdown: [
    { type: "investissement", balance: 10000, rate_pct: 6.5, source: "observed" },
    { type: "autres", balance: 5000, rate_pct: 2, source: "manual" },
  ],
  current_wealth: 15000,
  avg_monthly_savings: 420,
  months_used: 6,
  annual_return_pct: 5.1,
  years: 10,
  extra_monthly: 100,
  final_base: 0,
  final_boosted: 0,
  gain_from_extra: 0,
  points: [],
}

function setup(overrides: Partial<WealthForecastView> = {}, data: Partial<Forecast> = {}) {
  const ctx = partial<WealthForecastView>({
    data: { ...forecast, ...data },
    boostedShown: false,
    investInput: "",
    otherInput: "3",
    savingsInput: "",
    showMethod: true,
    showMonths: false,
    setInvestInput: vi.fn(),
    setOtherInput: vi.fn(),
    setSavingsInput: vi.fn(),
    setShowMethod: vi.fn(),
    setShowMonths: vi.fn(),
    ...overrides,
  })
  return { ctx, ...renderWithProviders(<ForecastMethodCard ctx={ctx} />) }
}

describe("ForecastMethodCard", () => {
  it("replié : seul l'en-tête s'affiche et le clic bascule le volet", async () => {
    const { ctx, user } = setup({ showMethod: false })

    expect(screen.queryByText("Ton point de départ")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { expanded: false })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { expanded: false }))
    expect(ctx.setShowMethod).toHaveBeenCalledTimes(1)
  })

  it("déplié : point de départ, durée de la moyenne et taux global retenu", () => {
    setup()

    expect(screen.getByText("Ton point de départ")).toBeInTheDocument()
    expect(screen.getByText(/15\s000,00\s€/)).toBeInTheDocument()
    expect(screen.getByText(/On répète pendant 10 ans/)).toBeInTheDocument()
    expect(screen.queryByText(/pour la courbe verte/)).not.toBeInTheDocument()
  })

  it("mentionne le complément mensuel quand la courbe verte est affichée", () => {
    setup({ boostedShown: true })

    expect(screen.getByText(/\+100 € pour la courbe verte/)).toBeInTheDocument()
  })

  it("saisie du montant d'épargne : placeholder arrondi, transmis au contexte ; pas de bouton de retour tant qu'il est calculé", async () => {
    const { ctx, user } = setup()

    const input = screen.getAllByRole("spinbutton")[0]
    expect(input).toHaveAttribute("placeholder", "420")
    await user.type(input, "5")
    expect(ctx.setSavingsInput).toHaveBeenCalledWith("5")
    expect(screen.queryByRole("button", { name: /Revenir au calcul/ })).not.toBeInTheDocument()
  })

  it("épargne saisie à la main : « Revenir au calcul » vide le champ", async () => {
    const { ctx, user } = setup({ savingsInput: "300" }, { savings_overridden: true })

    await user.click(screen.getByRole("button", { name: /Revenir au calcul/ }))
    expect(ctx.setSavingsInput).toHaveBeenCalledWith("")
  })

  it("détail mois par mois : le lien bascule, le tableau n'apparaît que déplié", async () => {
    const { ctx, user } = setup()

    await user.click(screen.getByRole("button", { name: "Voir le détail mois par mois" }))
    expect(ctx.setShowMonths).toHaveBeenCalledTimes(1)
  })

  it("tableau des mois déplié, sans lien quand il n'y a aucun mois", () => {
    setup({ showMonths: true })

    const row = screen.getByRole("row", { name: /mai 2026/ })
    expect(within(row).getByText(/3\s000,00\s€/)).toBeInTheDocument()
    expect(within(row).getByText("500,00 €", { exact: false, selector: "td.font-semibold" })).toBeInTheDocument()
  })

  it("sans mois exploitables : pas de lien de détail", () => {
    setup({}, { savings_months: [], months_used: 0 })

    expect(screen.queryByRole("button", { name: /détail mois par mois/ })).not.toBeInTheDocument()
  })

  it("taux par groupe : placeholder, saisie routée vers investissement ou autres, retour pour un taux manuel", async () => {
    const { ctx, user } = setup()

    const [, invest, other] = screen.getAllByRole("spinbutton")
    expect(invest).toHaveAttribute("placeholder", "6.5")
    expect(other).toHaveValue(3)

    await user.type(invest, "7")
    expect(ctx.setInvestInput).toHaveBeenCalledWith("7")
    await user.type(other, "1")
    expect(ctx.setOtherInput).toHaveBeenCalledWith("31")

    // Seul le groupe « autres » est en taux manuel
    await user.click(screen.getByRole("button", { name: /Revenir à/ }))
    expect(ctx.setOtherInput).toHaveBeenCalledWith("")
    expect(ctx.setInvestInput).not.toHaveBeenCalledWith("")
  })

  it("taux d'investissement manuel : le retour propose le taux observé", async () => {
    const { ctx, user } = setup({ investInput: "9" }, {
      return_breakdown: [{ type: "investissement", balance: 10000, rate_pct: 9, source: "manual" }],
    })

    const back = screen.getByRole("button", { name: /Revenir à/ })
    expect(back).toHaveTextContent("6,5")
    await user.click(back)
    expect(ctx.setInvestInput).toHaveBeenCalledWith("")
  })
})
