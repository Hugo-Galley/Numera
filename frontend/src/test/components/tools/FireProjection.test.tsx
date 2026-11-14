/** Projection FIRE : chargement, erreur avec nouvel essai, paramètres envoyés au backend et textes dérivés. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { FireProjection } from "@/components/tools/FireProjection"

const fire = {
  current_wealth: 60000,
  annual_expenses: 24000,
  expenses_overridden: false,
  withdrawal_rate_pct: 4,
  target: 600000,
  progress_pct: 10,
  monthly_savings: 800,
  savings_overridden: false,
  nominal_return_pct: 5,
  inflation_pct: 2,
  real_return_pct: 3,
  months_used: 6,
  years_to_fi: 14.5,
  fi_year: 2040,
  points: [{ year: 2026, wealth: 60000, target: 600000 }],
  scenarios: [
    { label: "Actuel", monthly_savings: 800, annual_expenses: 24000, years_to_fi: 14.5 },
    { label: "Épargne +100 €", monthly_savings: 900, annual_expenses: 24000, years_to_fi: 0 },
    { label: "Dépenses -10 %", monthly_savings: 800, annual_expenses: 21600, years_to_fi: 3 },
    { label: "Sans fin", monthly_savings: 0, annual_expenses: 24000, years_to_fi: null },
  ],
}

type FireOverrides = Partial<Omit<typeof fire, "years_to_fi">> & { years_to_fi?: number | null }

function serveFire(overrides: FireOverrides = {}) {
  const queries: URLSearchParams[] = []
  server.use(http.get(apiUrl("/analytics/fire"), ({ request }) => {
    queries.push(new URL(request.url).searchParams)
    return HttpResponse.json({ ...fire, ...overrides })
  }))
  return queries
}

describe("FireProjection", () => {
  it("affiche objectif, avancement, durée et date estimée, puis les scénarios", async () => {
    const queries = serveFire()
    renderWithProviders(<FireProjection />, { auth: true })

    expect(await screen.findByText("Indépendance financière")).toBeInTheDocument()
    expect(screen.getByText(/600\s000,00\s€/)).toBeInTheDocument()
    expect(screen.getAllByText("14 ans et 6 mois")).toHaveLength(2) // cartouche + scénario « Actuel »
    expect(screen.getByText("vers 2040")).toBeInTheDocument()
    expect(screen.getByText("déjà atteinte")).toBeInTheDocument()
    expect(screen.getByText("3 ans")).toBeInTheDocument()
    expect(screen.getByText("plus de 80 ans")).toBeInTheDocument()
    expect(queries[0].get("withdrawal_rate_pct")).toBe("4")
    expect(queries[0].has("annual_expenses")).toBe(false)
  })

  it("changer le taux de retrait relance le calcul avec ce taux", async () => {
    const queries = serveFire()
    const { user } = renderWithProviders(<FireProjection />, { auth: true })
    await screen.findByText("Indépendance financière")

    await user.click(screen.getByRole("button", { name: /^3,0\s?%$/ }))

    await waitFor(() => expect(queries.slice(-1)[0]?.get("withdrawal_rate_pct")).toBe("3"))
  })

  it("les hypothèses saisies sont envoyées ; un champ vide ou invalide est ignoré", async () => {
    const queries = serveFire()
    const { user } = renderWithProviders(<FireProjection />, { auth: true })
    await screen.findByText("Indépendance financière")

    await user.type(screen.getByLabelText("Dépenses / an (€)"), "18000")
    await user.type(screen.getByLabelText("Rendement (%)"), "6")

    await waitFor(() => {
      const last = queries.slice(-1)[0]
      expect(last.get("annual_expenses")).toBe("18000")
      expect(last.get("return_pct")).toBe("6")
      expect(last.has("monthly_savings")).toBe(false)
      expect(last.has("inflation_pct")).toBe(false)
    })
  })

  it("objectif hors de portée : message sur le rendement réel et bouton « 5 % » qui relance le calcul", async () => {
    const queries = serveFire({ years_to_fi: null, real_return_pct: -1, scenarios: [] })
    const { user } = renderWithProviders(<FireProjection />, { auth: true })

    expect(await screen.findByText(/l'inflation ronge l'épargne/)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Essayer avec 5 % de rendement" }))

    await waitFor(() => expect(queries.slice(-1)[0]?.get("return_pct")).toBe("5"))
    expect(screen.queryByRole("button", { name: "Essayer avec 5 % de rendement" })).not.toBeInTheDocument()
  })

  it("rendement réel positif mais objectif inaccessible : message sur le rythme d'épargne", async () => {
    serveFire({ years_to_fi: null, real_return_pct: 2 })
    renderWithProviders(<FireProjection />, { auth: true })

    expect(await screen.findByText(/n'est pas atteint avant 80 ans/)).toBeInTheDocument()
  })

  it("objectif déjà atteint : pas d'année estimée", async () => {
    serveFire({ years_to_fi: 0, fi_year: 2026 })
    renderWithProviders(<FireProjection />, { auth: true })

    await screen.findByText("Indépendance financière")
    expect(screen.queryByText(/vers 2026/)).not.toBeInTheDocument()
  })

  it("échec : message d'erreur puis « Réessayer » recharge", async () => {
    let fail = true
    server.use(http.get(apiUrl("/analytics/fire"), () => (fail ? new HttpResponse(null, { status: 500 }) : HttpResponse.json(fire))))
    const { user } = renderWithProviders(<FireProjection />, { auth: true })

    expect(await screen.findByText("Impossible de calculer la projection d'indépendance financière.")).toBeInTheDocument()
    fail = false
    await user.click(screen.getByRole("button", { name: /Réessayer/ }))

    expect(await screen.findByText("Indépendance financière")).toBeInTheDocument()
  })

  it("dépenses saisies : la note l'indique", async () => {
    serveFire({ expenses_overridden: true, savings_overridden: true })
    renderWithProviders(<FireProjection />, { auth: true })

    await screen.findByText("Indépendance financière")
    expect(screen.getByText(/saisies/i)).toBeInTheDocument()
  })
})
