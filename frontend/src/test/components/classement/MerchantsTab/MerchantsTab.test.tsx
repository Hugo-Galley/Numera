/** Marchands canoniques : liste et recherche, création, modification, variantes (alias), normalisation automatique, suggestions. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeCategory } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { MerchantsTab } from "@/components/classement/MerchantsTab"
import type { Merchant } from "@/components/classement/MerchantsTab/types"

const amazon: Merchant = { id: 1, name: "Amazon", category_id: 3, icon: null, color: "#f97316", aliases: [{ id: 11, merchant_id: 1, label: "AMZN DIGITAL" }, { id: 12, merchant_id: 1, label: "AMAZON.FR" }] }
const netflix: Merchant = { id: 2, name: "Netflix", category_id: null, icon: null, color: null, aliases: [] }

type Write = { method: string; path: string; body: unknown }

/** Marchands en mémoire ; chaque écriture est consignée (méthode, chemin, corps). */
function serve({ merchants = [amazon, netflix], suggestions = [{ label: "CB SPOTIFY", count: 7 }] }: { merchants?: Merchant[]; suggestions?: { label: string; count: number }[] } = {}) {
  const writes: Write[] = []
  const state = { merchants, loads: 0 }
  const note = async (request: Request, path: string) => {
    const text = await request.text()
    writes.push({ method: request.method, path, body: text ? JSON.parse(text) : null })
  }
  server.use(
    http.get(apiUrl("/merchants"), () => { state.loads += 1; return HttpResponse.json(state.merchants) }),
    http.get(apiUrl("/categories"), () => HttpResponse.json([makeCategory({ id: 3, name: "Shopping" })])),
    http.get(apiUrl("/merchants/suggestions/unnormalized"), () => HttpResponse.json(suggestions)),
    http.get(apiUrl("/merchants/:id"), ({ params }) => HttpResponse.json(state.merchants.find((m) => String(m.id) === params.id))),
    http.post(apiUrl("/merchants/auto-normalize"), async ({ request }) => { await note(request, "/merchants/auto-normalize"); return HttpResponse.json({ normalized_count: 4 }) }),
    http.post(apiUrl("/merchants/:id/aliases"), async ({ request, params }) => {
      await note(request, `/merchants/${params.id}/aliases`)
      state.merchants = state.merchants.map((m) => (String(m.id) === params.id ? { ...m, aliases: [...m.aliases, { id: 99, merchant_id: m.id, label: "AMZN MKTP" }] } : m))
      return HttpResponse.json({})
    }),
    http.post(apiUrl("/merchants"), async ({ request }) => { await note(request, "/merchants"); return HttpResponse.json({ id: 50 }) }),
    http.put(apiUrl("/merchants/:id"), async ({ request, params }) => { await note(request, `/merchants/${params.id}`); return HttpResponse.json({}) }),
    http.delete(apiUrl("/merchants/aliases/:id"), async ({ request, params }) => { await note(request, `/merchants/aliases/${params.id}`); return new HttpResponse(null, { status: 204 }) }),
    http.delete(apiUrl("/merchants/:id"), async ({ request, params }) => { await note(request, `/merchants/${params.id}`); return new HttpResponse(null, { status: 204 }) }),
  )
  return { writes, loads: () => state.loads }
}

const view = () => renderWithProviders(<MerchantsTab />, { auth: true })

describe("MerchantsTab : liste", () => {
  it("affiche les marchands avec leurs variantes, ou « Aucune variante définie »", async () => {
    serve()
    view()

    expect(await screen.findByText("Amazon")).toBeInTheDocument()
    expect(screen.getByText("AMZN DIGITAL")).toBeInTheDocument()
    expect(screen.getByText("AMAZON.FR")).toBeInTheDocument()
    expect(screen.getByText("Netflix")).toBeInTheDocument()
    expect(screen.getByText("Aucune variante définie")).toBeInTheDocument()
  })

  it("la recherche filtre par nom ou par variante ; sans résultat : message", async () => {
    serve()
    const { user } = view()
    await screen.findByText("Amazon")
    const search = screen.getByPlaceholderText("Rechercher un marchand ou un libellé...")

    await user.type(search, "amzn")
    expect(screen.getByText("Amazon")).toBeInTheDocument()
    expect(screen.queryByText("Netflix")).not.toBeInTheDocument()

    await user.clear(search)
    await user.type(search, "zzz")
    expect(await screen.findByText("Aucun marchand trouvé.")).toBeInTheDocument()
  })

  it("chargement en échec : message d'erreur", async () => {
    server.use(
      http.get(apiUrl("/merchants"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
      http.get(apiUrl("/categories"), () => HttpResponse.json([])),
      http.get(apiUrl("/merchants/suggestions/unnormalized"), () => HttpResponse.json([])),
    )
    view()

    expect(await screen.findByText("Erreur chargement données")).toBeInTheDocument()
  })
})

describe("MerchantsTab : création", () => {
  it("POST avec nom, catégorie « aucune », couleur par défaut et variantes séparées par des virgules", async () => {
    const { writes, loads } = serve()
    const { user } = view()
    await screen.findByText("Amazon")
    const before = loads()

    await user.click(screen.getByRole("button", { name: "Nouveau marchand" }))
    const dialog = await screen.findByRole("dialog", { name: "Nouveau marchand canonique" })
    await user.type(within(dialog).getByLabelText("Nom Canonique"), "Starbucks")
    await user.type(within(dialog).getByLabelText("Variantes (séparées par des virgules)"), "STARBUCKS PARIS, SBX ,  ,STARBUCKS FR")
    await user.click(within(dialog).getByRole("button", { name: "Créer le marchand" }))

    await waitFor(() => expect(writes).toEqual([{ method: "POST", path: "/merchants", body: { name: "Starbucks", category_id: null, color: "#64748b", aliases: ["STARBUCKS PARIS", "SBX", "STARBUCKS FR"] } }]))
    expect(await screen.findByText("Marchand ajouté")).toBeInTheDocument()
    await waitFor(() => expect(loads()).toBeGreaterThan(before))
  })

  it("nom vide : rien n'est envoyé", async () => {
    const { writes } = serve()
    const { user } = view()
    await screen.findByText("Amazon")

    await user.click(screen.getByRole("button", { name: "Nouveau marchand" }))
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Créer le marchand" }))

    expect(writes).toEqual([])
  })

  it("création refusée : message d'erreur", async () => {
    serve()
    server.use(http.post(apiUrl("/merchants"), () => HttpResponse.json({ detail: "KO" }, { status: 409 })))
    const { user } = view()
    await screen.findByText("Amazon")

    await user.click(screen.getByRole("button", { name: "Nouveau marchand" }))
    const dialog = await screen.findByRole("dialog")
    await user.type(within(dialog).getByLabelText("Nom Canonique"), "Starbucks")
    await user.click(within(dialog).getByRole("button", { name: "Créer le marchand" }))

    expect(await screen.findByText("Erreur lors de l'ajout")).toBeInTheDocument()
  })

  it("suggestion : « + » ouvre la création préremplie avec le libellé en nom et en variante", async () => {
    serve()
    const { user } = view()

    await user.click(await screen.findByRole("button", { name: "Créer un marchand à partir de ce libellé" }))

    const dialog = await screen.findByRole("dialog", { name: "Nouveau marchand canonique" })
    expect(within(dialog).getByLabelText("Nom Canonique")).toHaveValue("CB SPOTIFY")
    expect(within(dialog).getByLabelText("Variantes (séparées par des virgules)")).toHaveValue("CB SPOTIFY")
    expect(screen.getByText("7 occurrences")).toBeInTheDocument()
  })

  it("aucune suggestion : « Tout est normalisé »", async () => {
    serve({ suggestions: [] })
    view()

    expect(await screen.findByText(/Tout est normalisé/)).toBeInTheDocument()
  })
})

describe("MerchantsTab : modification", () => {
  async function openEdit(user: ReturnType<typeof view>["user"], name = "Amazon") {
    await screen.findByText(name)
    const card = screen.getByText(name).closest(".group") as HTMLElement
    await user.click(within(card).getByRole("button", { name: "Modifier" }))
    return screen.findByRole("dialog", { name: "Modifier le marchand" })
  }

  it("dialogue prérempli ; PUT avec le nom modifié, la catégorie et la couleur", async () => {
    const { writes } = serve()
    const { user } = view()
    const dialog = await openEdit(user)
    const name = within(dialog).getByLabelText("Nom Canonique")
    expect(name).toHaveValue("Amazon")
    expect(within(dialog).getByText("AMZN DIGITAL")).toBeInTheDocument()

    await user.clear(name)
    await user.type(name, "Amazon France")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "PUT", path: "/merchants/1", body: { name: "Amazon France", category_id: 3, color: "#f97316" } }]))
    expect(await screen.findByText("Marchand mis à jour")).toBeInTheDocument()
  })

  it("modification refusée : message d'erreur", async () => {
    serve()
    server.use(http.put(apiUrl("/merchants/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view()
    const dialog = await openEdit(user)

    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Erreur lors de la mise à jour")).toBeInTheDocument()
  })

  it("ajouter une variante : POST puis la liste du dialogue est relue", async () => {
    const { writes } = serve()
    const { user } = view()
    const dialog = await openEdit(user)

    await user.type(within(dialog).getByPlaceholderText("Nouvelle variante..."), "AMZN MKTP")
    await user.click(within(dialog).getByRole("button", { name: "Ajouter" }))

    await waitFor(() => expect(writes).toEqual([{ method: "POST", path: "/merchants/1/aliases", body: { label: "AMZN MKTP" } }]))
    expect(await within(dialog).findByText("AMZN MKTP")).toBeInTheDocument()
    expect(await screen.findByText("Alias ajouté")).toBeInTheDocument()
  })

  it("variante déjà existante : message d'erreur", async () => {
    serve()
    server.use(http.post(apiUrl("/merchants/:id/aliases"), () => HttpResponse.json({ detail: "existe" }, { status: 409 })))
    const { user } = view()
    const dialog = await openEdit(user)

    await user.type(within(dialog).getByPlaceholderText("Nouvelle variante..."), "AMZN DIGITAL")
    await user.click(within(dialog).getByRole("button", { name: "Ajouter" }))

    expect(await screen.findByText("L'alias existe déjà ou erreur")).toBeInTheDocument()
  })

  it("retirer une variante : DELETE et la variante disparaît du dialogue", async () => {
    const { writes } = serve()
    const { user } = view()
    const dialog = await openEdit(user)

    const alias = within(dialog).getByText("AMZN DIGITAL").closest("div, span") as HTMLElement
    await user.click(within(alias).getByRole("button", { name: "Fermer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "DELETE", path: "/merchants/aliases/11", body: null }]))
    await waitFor(() => expect(within(dialog).queryByText("AMZN DIGITAL")).not.toBeInTheDocument())
    expect(await screen.findByText("Alias supprimé")).toBeInTheDocument()
  })

  it("retrait d'une variante refusé : message d'erreur", async () => {
    serve()
    server.use(http.delete(apiUrl("/merchants/aliases/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view()
    const dialog = await openEdit(user)

    const alias = within(dialog).getByText("AMZN DIGITAL").closest("div, span") as HTMLElement
    await user.click(within(alias).getByRole("button", { name: "Fermer" }))

    expect(await screen.findByText("Erreur suppression alias")).toBeInTheDocument()
  })
})

describe("MerchantsTab : suppression et normalisation", () => {
  it("suppression confirmée : DELETE puis rechargement ; annulée : rien n'est envoyé", async () => {
    const { writes } = serve()
    const { user } = view()
    await screen.findByText("Netflix")
    const card = () => screen.getByText("Netflix").closest(".group") as HTMLElement

    await user.click(within(card()).getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))
    expect(writes).toEqual([])

    await user.click(within(card()).getByRole("button", { name: "Supprimer" }))
    const dialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(dialog).toHaveTextContent("Supprimer ce marchand canonique ?")
    await user.click(within(dialog).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "DELETE", path: "/merchants/2", body: null }]))
    expect(await screen.findByText("Marchand supprimé")).toBeInTheDocument()
  })

  it("suppression refusée : message d'erreur", async () => {
    serve()
    server.use(http.delete(apiUrl("/merchants/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view()
    await screen.findByText("Netflix")

    await user.click(within(screen.getByText("Netflix").closest(".group") as HTMLElement).getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Erreur lors de la suppression")).toBeInTheDocument()
  })

  it("« Auto-normaliser » : POST, nombre de transactions annoncé, liste rechargée", async () => {
    const { writes, loads } = serve()
    const { user } = view()
    await screen.findByText("Amazon")
    const before = loads()

    await user.click(screen.getByRole("button", { name: "Auto-normaliser" }))

    await waitFor(() => expect(writes).toEqual([{ method: "POST", path: "/merchants/auto-normalize", body: {} }]))
    expect(await screen.findByText("4 transactions normalisées")).toBeInTheDocument()
    await waitFor(() => expect(loads()).toBeGreaterThan(before))
  })

  it("normalisation refusée : message d'erreur", async () => {
    serve()
    server.use(http.post(apiUrl("/merchants/auto-normalize"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view()
    await screen.findByText("Amazon")

    await user.click(screen.getByRole("button", { name: "Auto-normaliser" }))

    expect(await screen.findByText("Erreur lors de la normalisation")).toBeInTheDocument()
  })
})
