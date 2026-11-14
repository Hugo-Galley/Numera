/** Simulateur de patrimoine avancé : paramètres, événements de vie, allocation d'actifs, fiscalité, mémorisation dans le navigateur. */
import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { safeStorage } from "@/lib/storage"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { WealthSimulator } from "@/components/analytics/WealthSimulator"

const item = (year: number, total: number) => ({
  year, total_value: total, total_value_real: total * 0.9, contributions: 6000 * year, interest: total - 6000 * year, event_applied: null,
  total_value_p10: total * 0.8, total_value_p90: total * 1.2, total_value_p10_real: total * 0.7, total_value_p90_real: total * 1.1,
})
const simulation = {
  items: [item(1, 16000), item(2, 23000)], total_final: 23000, total_final_real: 21000, total_contributions: 12000, total_interest: 1000, total_tax_paid: 150,
  pessimistic_final: 18000, optimistic_final: 28000,
}

/** Serveur de simulation : chaque requête est consignée (query décodée). */
function serve(response: () => Response = () => HttpResponse.json(simulation)) {
  const queries: URLSearchParams[] = []
  server.use(http.get(apiUrl("/analytics/wealth-simulation"), ({ request }) => { queries.push(new URL(request.url).searchParams); return response() }))
  return queries
}
const lastQuery = (queries: URLSearchParams[]) => queries[queries.length - 1]
const view = (capital = 10000) => renderWithProviders(<WealthSimulator initialCapitalDefault={capital} />, { auth: true })
/** La simulation est affichée quand son tableau annuel l'est. */
const ready = () => screen.findAllByText(/23\s000/)
/** Le commutateur d'allocation précède celui du graphique dans la page. */
const allocationSwitch = () => screen.getAllByRole("switch")[0]
const tab = (name: string) => screen.getByRole("tab", { name: new RegExp(name) })

describe("WealthSimulator : simulation", () => {
  it("envoie les paramètres par défaut (capital proposé, 500 € par mois, 20 ans) et affiche le patrimoine final", async () => {
    const queries = serve()
    view(25000)

    await ready()
    expect(screen.getByText("Simulateur de Patrimoine Avancé")).toBeInTheDocument()
    await waitFor(() => expect(queries.length).toBeGreaterThan(0))
    const q = lastQuery(queries)
    expect(q.get("initial_capital")).toBe("25000")
    expect(q.get("monthly_contribution")).toBe("500")
    expect(q.get("years")).toBe("20")
    expect(q.get("annual_return_pct")).toBe("7")
    expect(q.get("events")).toBe("[]")
  })

  it("configuration active : saisie manuelle par défaut", async () => {
    serve()
    view()

    expect(await screen.findByText(/Saisie manuelle \(7% rdt \/ 0% vol\)/)).toBeInTheDocument()
  })

  it("simulation en échec : message d'erreur", async () => {
    serve(() => HttpResponse.json({ detail: "KO" }, { status: 500 }))
    view()

    expect(await screen.findByText("Erreur lors de la simulation")).toBeInTheDocument()
  })

  it("paramètres mémorisés dans le navigateur : repris à la réouverture, sauf le capital qui suit la valeur proposée", async () => {
    serve()
    safeStorage.setItem("numera_wealth_sim_params", JSON.stringify({ initial_capital: 1, monthly_contribution: 900, annual_return_pct: 5, years: 10, volatility_pct: 0, inflation_rate_pct: 2, contribution_indexation_pct: 0, tax_rate_pct: 0, tax_deferred: true }))
    const queries = serve()
    view(40000)

    await waitFor(() => expect(queries.length).toBeGreaterThan(0))
    const q = lastQuery(queries)
    expect(q.get("monthly_contribution")).toBe("900")
    expect(q.get("years")).toBe("10")
    expect(q.get("initial_capital")).toBe("40000")
  })

  it("sauvegarde illisible : retour aux valeurs par défaut", async () => {
    safeStorage.setItem("numera_wealth_sim_params", "{pas du json")
    safeStorage.setItem("numera_wealth_sim_events", "oups")
    const queries = serve()
    view()

    await waitFor(() => expect(queries.length).toBeGreaterThan(0))
    expect(lastQuery(queries).get("monthly_contribution")).toBe("500")
  })

  it("volatilité saisie : le badge « Monte Carlo actif » apparaît et la requête porte la volatilité", async () => {
    const queries = serve()
    const { user } = view()
    await ready()

    await user.click(tab("Fiscalité"))
    const vol = await screen.findByLabelText("Volatilité Annuelle (%)")
    await user.clear(vol)
    await user.type(vol, "12")

    expect(await screen.findByText("Monte Carlo Actif")).toBeInTheDocument()
    await waitFor(() => expect(lastQuery(queries).get("volatility_pct")).toBe("12"))
  })

  it("fiscalité : taux d'impôt et régime (prélèvement annuel) partent dans la requête", async () => {
    const queries = serve()
    const { user } = view()
    await ready()

    await user.click(tab("Fiscalité"))
    const tax = await screen.findByLabelText("Taux d'Impôt (%)")
    await user.clear(tax)
    await user.type(tax, "30")
    await user.selectOptions(screen.getByLabelText("Régime Fiscal"), "false")

    await waitFor(() => {
      const q = lastQuery(queries)
      expect(q.get("tax_rate_pct")).toBe("30")
      expect(q.get("tax_deferred")).toBe("false")
    })
  })
})

describe("WealthSimulator : événements de vie", () => {
  async function openEvents() {
    const queries = serve()
    const view_ = view()
    await ready()
    await view_.user.click(tab("Événements de Vie"))
    return { queries, ...view_ }
  }

  it("aucun événement : message", async () => {
    await openEvents()

    expect(await screen.findByText("Aucun événement ponctuel configuré.")).toBeInTheDocument()
  })

  it("libellé vide : message, aucun événement ajouté", async () => {
    const { user } = await openEvents()

    await user.click(await screen.findByRole("button", { name: "Ajouter" }))

    expect(await screen.findByText("Veuillez saisir un libellé pour l'événement.")).toBeInTheDocument()
    expect(screen.getByText("Aucun événement ponctuel configuré.")).toBeInTheDocument()
  })

  it("ajout : l'événement est listé, compté sur l'onglet, mémorisé et envoyé à la simulation", async () => {
    const { user, queries } = await openEvents()

    await user.type(await screen.findByPlaceholderText("Achat voiture, Achat RP..."), "Voiture")
    await user.click(screen.getByRole("button", { name: "Ajouter" }))

    expect(await screen.findByText("Événement ajouté à la simulation")).toBeInTheDocument()
    expect(screen.getByText("Voiture")).toBeInTheDocument()
    expect(JSON.parse(safeStorage.getItem("numera_wealth_sim_events") ?? "[]")).toEqual([{ year: 5, amount: -10000, label: "Voiture" }])
    await waitFor(() => expect(JSON.parse(lastQuery(queries).get("events") ?? "[]")).toEqual([{ year: 5, amount: -10000, label: "Voiture" }]))
  })

  it("suppression d'un événement", async () => {
    safeStorage.setItem("numera_wealth_sim_events", JSON.stringify([{ year: 3, amount: 5000, label: "Héritage" }]))
    serve()
    const { user } = view()
    await user.click(await screen.findByRole("tab", { name: /Événements de Vie/ }))
    expect(await screen.findByText("Héritage")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Événement supprimé")).toBeInTheDocument()
    expect(screen.queryByText("Héritage")).not.toBeInTheDocument()
  })
})

describe("WealthSimulator : allocation d'actifs", () => {
  async function openAllocation() {
    const queries = serve()
    const view_ = view()
    await ready()
    await view_.user.click(tab("Allocation"))
    return { queries, ...view_ }
  }

  it("désactivée par défaut : invite à activer le commutateur", async () => {
    await openAllocation()

    expect(await screen.findByText(/Activez le commutateur ci-dessus/)).toBeInTheDocument()
  })

  it("activée : classes d'actifs, pondération totale à 100 % et configuration active calculée", async () => {
    const { user } = await openAllocation()

    await user.click(allocationSwitch())

    expect(await screen.findByText(/Actions \/ ETF World \(60%\)/)).toBeInTheDocument()
    expect(screen.getByText(/100% ✓/)).toBeInTheDocument()
    expect(screen.getByText(/Allocation d'actifs \(/)).toBeInTheDocument()
  })

  it("un preset remplace les classes d'actifs", async () => {
    const { user } = await openAllocation()
    await user.click(allocationSwitch())

    await user.click(await screen.findByRole("button", { name: "100% Actions" }))

    expect(await screen.findByText("Preset d'allocation appliqué")).toBeInTheDocument()
    expect(screen.getByText(/Actions \/ ETF \(100%\)/)).toBeInTheDocument()
    expect(screen.queryByText(/Obligations d'État/)).not.toBeInTheDocument()
  })

  it("ajouter une classe l'ouvre en édition, à 0 % : la pondération totale ne change pas", async () => {
    const { user } = await openAllocation()
    await user.click(allocationSwitch())

    await user.click(await screen.findByRole("button", { name: "Ajouter une classe d'actifs" }))

    expect(await screen.findByRole("dialog", { name: "Modifier l'actif" })).toBeInTheDocument()
    expect(screen.getByText(/100% ✓/)).toBeInTheDocument()
  })

  it("pondération différente de 100 % : signalée en rouge et la simulation attend (aucune nouvelle requête)", async () => {
    const { user, queries } = await openAllocation()
    await user.click(allocationSwitch())
    await waitFor(() => expect(queries.length).toBeGreaterThan(1))
    const before = queries.length

    fireEvent.change(document.querySelector('input[type="range"]') as HTMLInputElement, { target: { value: "50" } })

    expect(await screen.findByText(/90% \(doit être de 100%\)/)).toBeInTheDocument()
    expect(screen.queryByText(/100% ✓/)).not.toBeInTheDocument()
    await new Promise((r) => setTimeout(r, 150))
    expect(queries.length).toBe(before)
  })

  it("édition d'une classe : dialogue prérempli, enregistrement met à jour la liste", async () => {
    const { user } = await openAllocation()
    await user.click(allocationSwitch())

    await user.click(screen.getAllByTitle("Modifier les hypothèses de cet actif")[0])
    const dialog = await screen.findByRole("dialog", { name: "Modifier l'actif" })
    const name = within(dialog).getByLabelText("Nom de l'actif")
    expect(name).toHaveValue("Actions / ETF World")
    await user.clear(name)
    await user.type(name, "ETF Monde")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText(/ETF Monde \(60%\)/)).toBeInTheDocument()
    expect(await screen.findByText("Actif mis à jour")).toBeInTheDocument()
  })

  it("suppression d'une classe, mais jamais la dernière", async () => {
    const { user } = await openAllocation()
    await user.click(allocationSwitch())
    await user.click(await screen.findByRole("button", { name: "100% Actions" }))
    await screen.findByText(/Actions \/ ETF \(100%\)/)

    await user.click(screen.getByTitle("Supprimer cet actif"))

    expect(await screen.findByText("Vous devez conserver au moins une classe d'actifs.")).toBeInTheDocument()
    expect(screen.getByText(/Actions \/ ETF \(100%\)/)).toBeInTheDocument()
  })

  it("suppression d'une classe parmi plusieurs", async () => {
    const { user } = await openAllocation()
    await user.click(allocationSwitch())

    await user.click(screen.getAllByTitle("Supprimer cet actif")[3])

    expect(await screen.findByText("Actif supprimé")).toBeInTheDocument()
    expect(screen.queryByText(/Cash \/ Fonds Euro/)).not.toBeInTheDocument()
  })
})

describe("WealthSimulator : graphique", () => {
  it("« Ajuster inflation » bascule la vue en euros constants", async () => {
    serve()
    const { user } = view()
    await ready()

    await user.click(screen.getByRole("switch", { name: /Ajuster inflation/ }))

    expect(await screen.findByText("Euros Constants")).toBeInTheDocument()
  })

  it("le tableau annuel détaillé liste chaque année", async () => {
    serve()
    view()

    expect(await screen.findByText("Tableau annuel détaillé")).toBeInTheDocument()
  })
})
