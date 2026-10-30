/** Règles de catégorisation : liste, création (corps envoyé), suppression confirmée, application à l'existant. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeCategory } from "@/test/factories"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { RulesTab } from "./RulesTab"

interface Rule {
  id: number
  pattern: string
  category_id: number | null
  merchant_name: string | null
  transaction_type: string | null
  priority: number
}

/** Règles en mémoire : POST ajoute, DELETE retire ; les écritures sont consignées. */
function serveRules(initial: Rule[] = []) {
  const state = { rules: [...initial], writes: [] as { method: string; path: string; body: unknown }[] }
  server.use(
    http.get(apiUrl("/categorization-rules/"), () => HttpResponse.json(state.rules)),
    http.get(apiUrl("/categories"), () => HttpResponse.json([makeCategory({ id: 3, name: "Transport" })])),
    http.post(apiUrl("/categorization-rules/"), async ({ request }) => {
      const body = (await request.json()) as Omit<Rule, "id">
      state.writes.push({ method: "POST", path: "/categorization-rules/", body })
      state.rules.push({ id: 50, ...body })
      return HttpResponse.json({ id: 50, ...body })
    }),
    http.delete(apiUrl("/categorization-rules/:id"), ({ params }) => {
      state.writes.push({ method: "DELETE", path: `/categorization-rules/${params.id}`, body: null })
      state.rules = state.rules.filter((r) => String(r.id) !== params.id)
      return new HttpResponse(null, { status: 204 })
    }),
  )
  return state
}

const UBER: Rule = { id: 1, pattern: "UBER", category_id: 3, merchant_name: "Uber", transaction_type: "Sortie", priority: 5 }

describe("RulesTab", () => {
  it("chargement puis liste : motif, marchand renommé, catégorie, type forcé, priorité", async () => {
    serveRules([UBER])
    renderWithProviders(<RulesTab />, { auth: true })

    expect(screen.getByText("Chargement...")).toBeInTheDocument()
    expect(await screen.findByText("UBER")).toBeInTheDocument()
    expect(screen.getByText("Uber")).toBeInTheDocument()
    expect(screen.getByText("Transport")).toBeInTheDocument()
    expect(screen.getByText("Type → Sortie")).toBeInTheDocument()
    expect(screen.getByText("Priorité: 5")).toBeInTheDocument()
  })

  it("aucune règle : état vide", async () => {
    serveRules()
    renderWithProviders(<RulesTab />, { auth: true })

    expect(await screen.findByText(/Aucune règle définie/)).toBeInTheDocument()
  })

  it("échec du chargement : toast d'erreur", async () => {
    serveRules()
    server.use(http.get(apiUrl("/categorization-rules/"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))
    renderWithProviders(<RulesTab />, { auth: true })

    expect(await screen.findByText("Impossible de charger les règles")).toBeInTheDocument()
  })

  it.todo(
    "échec du chargement (GET /categorization-rules/ → 500) : la liste affiche « Aucune règle définie… » comme s'il n'y en avait pas ; " +
      "attendu un ErrorState avec « Réessayer » (components/classement/RulesTab.tsx, loadData)",
  )

  it("création : POST avec catégorie numérique, type null si « Aucun changement », toast et liste rechargée", async () => {
    const state = serveRules()
    const { user } = renderWithProviders(<RulesTab />, { auth: true })
    await screen.findByText(/Aucune règle définie/)

    await user.click(screen.getByRole("button", { name: "Nouvelle règle" }))
    const dialog = screen.getByRole("dialog", { name: "Ajouter une règle" })
    // Libellés non reliés aux champs : catégorie = 1re liste, type = 2e
    await user.type(within(dialog).getByPlaceholderText(/Uber, Netflix/), "NETFLIX")
    await user.click(within(dialog).getAllByRole("combobox")[0])
    await user.click(screen.getByRole("option", { name: "Transport" }))
    await user.type(within(dialog).getByPlaceholderText("Nom propre du marchand"), "Netflix")
    await user.clear(within(dialog).getByRole("spinbutton"))
    await user.type(within(dialog).getByRole("spinbutton"), "2")
    await user.click(within(dialog).getByRole("button", { name: "Créer la règle" }))

    expect(await screen.findByText("Règle créée avec succès")).toBeInTheDocument()
    expect(state.writes).toEqual([
      {
        method: "POST",
        path: "/categorization-rules/",
        body: { pattern: "NETFLIX", category_id: 3, merchant_name: "Netflix", transaction_type: null, priority: 2 },
      },
    ])
    expect(await screen.findByText("NETFLIX")).toBeInTheDocument()
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("création avec type forcé en Entrée", async () => {
    const state = serveRules()
    const { user } = renderWithProviders(<RulesTab />, { auth: true })
    await screen.findByText(/Aucune règle définie/)

    await user.click(screen.getByRole("button", { name: "Nouvelle règle" }))
    const dialog = screen.getByRole("dialog", { name: "Ajouter une règle" })
    await user.type(within(dialog).getByPlaceholderText(/Uber, Netflix/), "REMB")
    await user.click(within(dialog).getAllByRole("combobox")[1])
    await user.click(screen.getByRole("option", { name: "Forcer en Entrée" }))
    await user.click(within(dialog).getByRole("button", { name: "Créer la règle" }))

    await screen.findByText("Règle créée avec succès")
    expect(state.writes[0].body).toMatchObject({ pattern: "REMB", category_id: null, transaction_type: "Entree" })
    expect(await screen.findByText("Type → Entrée")).toBeInTheDocument()
  })

  it("sans mot-clé : rien n'est envoyé, le dialogue reste ouvert", async () => {
    const state = serveRules()
    const { user } = renderWithProviders(<RulesTab />, { auth: true })
    await screen.findByText(/Aucune règle définie/)

    await user.click(screen.getByRole("button", { name: "Nouvelle règle" }))
    await user.click(screen.getByRole("button", { name: "Créer la règle" }))

    expect(state.writes).toEqual([])
    expect(screen.getByRole("dialog", { name: "Ajouter une règle" })).toBeInTheDocument()
  })

  it("création en échec : toast, dialogue ouvert", async () => {
    serveRules()
    server.use(http.post(apiUrl("/categorization-rules/"), () => HttpResponse.json({ detail: "doublon" }, { status: 400 })))
    const { user } = renderWithProviders(<RulesTab />, { auth: true })
    await screen.findByText(/Aucune règle définie/)

    await user.click(screen.getByRole("button", { name: "Nouvelle règle" }))
    await user.type(screen.getByPlaceholderText(/Uber, Netflix/), "UBER")
    await user.click(screen.getByRole("button", { name: "Créer la règle" }))

    expect(await screen.findByText("Échec de la création")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Ajouter une règle" })).toBeInTheDocument()
  })

  it("suppression confirmée : DELETE, toast, règle retirée", async () => {
    const state = serveRules([UBER])
    const { user } = renderWithProviders(<RulesTab />, { auth: true })
    await screen.findByText("UBER")

    await user.click(screen.getByRole("button", { name: "Supprimer" }))
    const confirmDialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(confirmDialog).toHaveTextContent("Supprimer cette règle ?")
    await user.click(within(confirmDialog).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Règle supprimée")).toBeInTheDocument()
    expect(state.writes).toEqual([{ method: "DELETE", path: "/categorization-rules/1", body: null }])
    await waitFor(() => expect(screen.queryByText("UBER")).not.toBeInTheDocument())
  })

  it("suppression annulée : aucune requête, règle conservée", async () => {
    const state = serveRules([UBER])
    const { user } = renderWithProviders(<RulesTab />, { auth: true })
    await screen.findByText("UBER")

    await user.click(screen.getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    expect(state.writes).toEqual([])
    expect(screen.getByText("UBER")).toBeInTheDocument()
  })

  it("« Appliquer à l'existant » : nombre de transactions modifiées", async () => {
    serveRules([UBER])
    server.use(http.post(apiUrl("/categorization-rules/apply-all"), () => HttpResponse.json({ modified_count: 12 })))
    const { user } = renderWithProviders(<RulesTab />, { auth: true })
    await screen.findByText("UBER")

    await user.click(screen.getByRole("button", { name: "Appliquer à l'existant" }))

    expect(await screen.findByText("12 transactions mises à jour")).toBeInTheDocument()
  })
})
