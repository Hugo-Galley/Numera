/** Échéances : liste des récurrences (modifier, activer, supprimer, générer) et détections d'abonnements (confirmer, ignorer). */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { safeStorage } from "@/lib/storage"
import { apiUrl } from "@/test/support/handlers"
import { makeAccount, makeCategory } from "@/test/support/factories"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import RecurringTransactions from "@/pages/RecurringTransactions"

const account = makeAccount({ id: 3, name: "Courant", type: "courant" })
const rent = {
  id: 10, account_id: 3, name: "Loyer", type: "Sortie", amount: 750, currency: "EUR", category_id: null, frequency: "monthly",
  day_of_month: 5, excluded_months: null, start_date: "2026-01-05T00:00:00", end_date: null, last_generated_date: "2026-06-05T00:00:00",
  is_active: true, auto_generate: true, note: null,
}
const gym = { ...rent, id: 11, name: "Salle de sport", amount: 30, is_active: false, auto_generate: false, last_generated_date: null }



/** Récurrences en mémoire ; chaque écriture est consignée. */
function serve({ recurrences = [rent, gym] as object[], subscriptions = [] as object[] } = {}) {
  const writes: { method: string; path: string; body: unknown }[] = []
  let loads = 0
  const note = async (request: Request, path: string) => {
    const text = await request.text()
    writes.push({ method: request.method, path, body: text ? JSON.parse(text) : null })
  }
  server.use(
    http.get(apiUrl("/recurring-transactions/"), () => { loads += 1; return HttpResponse.json(recurrences) }),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([account])),
    http.get(apiUrl("/categories"), () => HttpResponse.json([makeCategory({ id: 4, name: "Loisirs" })])),
    http.get(apiUrl("/analytics/subscriptions"), () => HttpResponse.json({ subscriptions, totals_by_kind: { subscriptions: { monthly: 12.99, annual: 155.88 } } })),
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    http.patch(apiUrl("/recurring-transactions/:id"), async ({ request, params }) => { await note(request, `/recurring-transactions/${params.id}`); return HttpResponse.json({}) }),
    http.delete(apiUrl("/recurring-transactions/:id"), async ({ request, params }) => { await note(request, `/recurring-transactions/${params.id}`); return new HttpResponse(null, { status: 204 }) }),
    http.post(apiUrl("/recurring-transactions/trigger"), async ({ request }) => { await note(request, "/recurring-transactions/trigger"); return HttpResponse.json(3) }),
    http.post(apiUrl("/analytics/subscriptions/ignore"), async ({ request }) => { await note(request, "/analytics/subscriptions/ignore"); return HttpResponse.json({}) }),
  )
  return { writes, loads: () => loads }
}

const view = (mode: "list" | "analysis") => {
  safeStorage.setItem("recurring-view", mode)
  return renderWithProviders(<RecurringTransactions />, { route: "/recurring", auth: true })
}
/** La liste rend une carte mobile et une ligne de tableau (masquée en CSS) : on pilote le tableau. */
const table = () => within(screen.getByRole("table"))
const row = (name: string) => within(screen.getAllByRole("row").find((r) => within(r).queryByText(name))!)

/** La case « Actif » est la dernière de la ligne (après « Auto »). */
const lastCheckbox = (name: string) => { const boxes = row(name).getAllByRole("checkbox"); return boxes[boxes.length - 1] }

describe("Échéances : liste", () => {
  it("affiche chaque récurrence avec son montant et sa dernière génération", async () => {
    serve()
    view("list")

    expect(await table().findByText("Loyer")).toBeInTheDocument()
    expect(table().getByText("Salle de sport")).toBeInTheDocument()
    expect(table().getByText(/750,00/)).toBeInTheDocument()
    expect(table().getByText("Aucune")).toBeInTheDocument()
  })

  it("aucune récurrence : message d'état vide", async () => {
    serve({ recurrences: [] })
    view("list")

    expect((await screen.findAllByText("Aucune transaction récurrente configurée.")).length).toBeGreaterThan(0)
  })

  it("chargement en échec : message d'erreur", async () => {
    server.use(
      http.get(apiUrl("/recurring-transactions/"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
      http.get(apiUrl("/accounts"), () => HttpResponse.json([account])),
      http.get(apiUrl("/categories"), () => HttpResponse.json([])),
      http.get(apiUrl("/analytics/subscriptions"), () => HttpResponse.json({ subscriptions: [] })),
      http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    )
    view("list")

    expect(await screen.findByText("Erreur lors du chargement des données")).toBeInTheDocument()
  })

  it("« Modifier » ouvre le formulaire prérempli avec la récurrence", async () => {
    serve()
    const { user } = view("list")
    await table().findByText("Loyer")

    await user.click(row("Loyer").getByRole("button", { name: "Modifier" }))

    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByDisplayValue("Loyer")).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue("750")).toBeInTheDocument()
  })

  it("case « Actif » : PATCH is_active inversé puis rechargement", async () => {
    const served = serve()
    const { user } = view("list")
    await table().findByText("Salle de sport")
    const before = served.loads()

    await user.click(lastCheckbox("Salle de sport"))

    await waitFor(() => expect(served.writes).toEqual([{ method: "PATCH", path: "/recurring-transactions/11", body: { is_active: true } }]))
    await waitFor(() => expect(served.loads()).toBeGreaterThan(before))
  })

  it("case « Actif » refusée : message d'erreur", async () => {
    serve()
    server.use(http.patch(apiUrl("/recurring-transactions/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view("list")
    await table().findByText("Loyer")

    await user.click(lastCheckbox("Loyer"))

    expect(await screen.findByText("Erreur lors de la modification")).toBeInTheDocument()
  })

  it("suppression confirmée : DELETE puis rechargement ; refusée : rien n'est envoyé", async () => {
    const served = serve()
    const { user } = view("list")
    await table().findByText("Loyer")

    await user.click(row("Loyer").getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))
    expect(served.writes).toEqual([])

    await user.click(row("Loyer").getByRole("button", { name: "Supprimer" }))
    const dialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(dialog).toHaveTextContent("Êtes-vous sûr de vouloir supprimer cette récurrence ?")
    await user.click(within(dialog).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(served.writes).toEqual([{ method: "DELETE", path: "/recurring-transactions/10", body: null }]))
    expect(await screen.findByText("Transaction récurrente supprimée")).toBeInTheDocument()
  })

  it("« Lancer la génération » : POST trigger, nombre de transactions générées annoncé", async () => {
    const served = serve()
    const { user } = view("list")
    await table().findByText("Loyer")

    await user.click(screen.getByRole("button", { name: "Lancer la génération" }))

    await waitFor(() => expect(served.writes).toEqual([{ method: "POST", path: "/recurring-transactions/trigger", body: {} }]))
    expect(await screen.findByText("3 transactions générées")).toBeInTheDocument()
  })

  it("génération en échec : message d'erreur", async () => {
    serve()
    server.use(http.post(apiUrl("/recurring-transactions/trigger"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view("list")
    await table().findByText("Loyer")

    await user.click(screen.getByRole("button", { name: "Lancer la génération" }))

    expect(await screen.findByText("Erreur lors de la génération")).toBeInTheDocument()
  })
})

describe("Échéances : analyse des abonnements", () => {
  const confirmed = { name: "Netflix", amount: 12.99, monthly_cost: 12.99, kind: "subscriptions", is_recurring_entity: true, in_kind_total: true, next_occurrence: "2026-07-01" }
  const detected = { name: "Spotify", amount: 10.99, kind: "subscriptions", is_recurring_entity: false, category_name: "Loisirs" }

  it("sépare abonnements confirmés et détections à valider, avec le coût mensuel total", async () => {
    serve({ subscriptions: [confirmed, detected] })
    view("analysis")

    // Netflix figure dans la liste confirmée et dans la répartition mensuelle
    expect((await screen.findAllByText("Netflix")).length).toBeGreaterThan(0)
    expect(screen.getByText("Spotify")).toBeInTheDocument()
    expect(screen.getByText("Détections intelligentes")).toBeInTheDocument()
    expect(screen.getAllByText(/12,99/).length).toBeGreaterThan(0)
  })

  it("« Confirmer » une détection ouvre le formulaire prérempli (nom, montant, catégorie)", async () => {
    serve({ subscriptions: [detected] })
    const { user } = view("analysis")
    await screen.findByText("Spotify")

    await user.click(screen.getByRole("button", { name: "Confirmer" }))

    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByDisplayValue("Spotify")).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue("10.99")).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue("Validé depuis détection automatique")).toBeInTheDocument()
  })

  it("« Invest. » ouvre le formulaire en versement", async () => {
    serve({ subscriptions: [detected] })
    const { user } = view("analysis")
    await screen.findByText("Spotify")

    await user.click(screen.getByRole("button", { name: "Invest." }))

    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByDisplayValue("Validé comme investissement")).toBeInTheDocument()
  })

  it("« Ignorer » une détection : confirmation puis POST ignore avec le marchand et le montant", async () => {
    const served = serve({ subscriptions: [detected] })
    const { user } = view("analysis")
    await screen.findByText("Spotify")

    await user.click(screen.getByRole("button", { name: "Ignorer" }))
    const dialog = await screen.findByRole("dialog", { name: "Ignorer la suggestion" })
    await user.click(within(dialog).getByRole("button", { name: "Ne plus suggérer" }))

    await waitFor(() => expect(served.writes).toEqual([{ method: "POST", path: "/analytics/subscriptions/ignore", body: { merchant: "Spotify", amount: 10.99 } }]))
    expect(await screen.findByText("Suggestion ignorée")).toBeInTheDocument()
  })

  it("ignorer refusé par le serveur : message d'erreur", async () => {
    serve({ subscriptions: [detected] })
    server.use(http.post(apiUrl("/analytics/subscriptions/ignore"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view("analysis")
    await screen.findByText("Spotify")

    await user.click(screen.getByRole("button", { name: "Ignorer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Ignorer la suggestion" })).getByRole("button", { name: "Ne plus suggérer" }))

    expect(await screen.findByText("Erreur lors de l'opération")).toBeInTheDocument()
  })

  it("changer d'onglet (Investissements) change les listes affichées", async () => {
    serve({ subscriptions: [confirmed, { ...confirmed, name: "PEA mensuel", kind: "investments" }] })
    const { user } = view("analysis")
    await screen.findAllByText("Netflix")

    await user.click(screen.getByRole("button", { name: "Investissements" }))

    expect((await screen.findAllByText("PEA mensuel")).length).toBeGreaterThan(0)
    expect(screen.queryByText("Netflix")).not.toBeInTheDocument()
  })
})
