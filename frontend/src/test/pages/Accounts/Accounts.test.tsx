/** Page Comptes : liste et tri, favori, création, modification (logo propagé), archivage et réactivation. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import Accounts from "@/pages/Accounts/index"

type Row = ReturnType<typeof makeAccount> & { active: boolean; is_main?: boolean; institution?: string | null; logo?: string | null }
const row = (overrides: Partial<Row>): Row => ({ ...makeAccount(), active: true, ...overrides })

/** Comptes en mémoire : POST/PATCH/DELETE modifient l'état et sont consignés (méthode, chemin, corps). */
function serveAccounts(initial: Row[]) {
  const state = { accounts: initial, writes: [] as { method: string; path: string; body: unknown }[] }
  const note = async (request: Request, path: string) => {
    const text = await request.text()
    const body = text ? JSON.parse(text) : null
    state.writes.push({ method: request.method, path, body })
    return body
  }
  server.use(
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json({ asset_classes: [], sectors: [], geographic_zones: [] })),
    http.get(apiUrl("/accounts"), () => HttpResponse.json(state.accounts)),
    http.post(apiUrl("/accounts"), async ({ request }) => {
      const body = await note(request, "/accounts")
      const created = row({ id: 99, ...body })
      state.accounts = [...state.accounts, created]
      return HttpResponse.json(created)
    }),
    http.patch(apiUrl("/accounts/:id"), async ({ request, params }) => {
      const body = await note(request, `/accounts/${params.id}`)
      state.accounts = state.accounts.map((a) => (String(a.id) === params.id ? { ...a, ...body } : a))
      return HttpResponse.json({})
    }),
    http.delete(apiUrl("/accounts/:id"), async ({ request, params }) => {
      await note(request, `/accounts/${params.id}`)
      state.accounts = state.accounts.map((a) => (String(a.id) === params.id ? { ...a, active: false } : a))
      return new HttpResponse(null, { status: 204 })
    }),
  )
  return state
}

const livret = row({ id: 1, name: "Livret perso", type: "epargne", balance: 1234.5, institution: "BRED" })
const courant = row({ id: 2, name: "Compte joint", type: "courant", balance: 500, institution: "BRED", is_main: true })
const view = () => renderWithProviders(<Accounts />, { route: "/accounts", auth: true })
const names = () => screen.getAllByRole("row").slice(1).map((r) => within(r).queryByText(/Livret perso|Compte joint|Zeta/)?.textContent)

describe("page Comptes : liste", () => {
  it("affiche les comptes actifs avec établissement, type et solde", async () => {
    serveAccounts([livret, courant])
    view()

    expect((await screen.findAllByText("Livret perso")).length).toBeGreaterThan(0)
    expect(screen.getAllByText("Compte joint").length).toBeGreaterThan(0)
    expect(screen.getAllByText(/1\s?234,50/).length).toBeGreaterThan(0)
  })

  it("aucun compte : message d'état vide", async () => {
    serveAccounts([])
    view()

    expect((await screen.findAllByText("Aucun compte trouvé.")).length).toBeGreaterThan(0)
  })

  it("chargement en échec : message d'erreur", async () => {
    server.use(
      http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json({ asset_classes: [], sectors: [], geographic_zones: [] })),
      http.get(apiUrl("/accounts"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
    )
    view()

    expect(await screen.findByText("Erreur lors du chargement des comptes")).toBeInTheDocument()
  })

  it("le compte principal reste en tête, puis le tri par nom bascule croissant/décroissant", async () => {
    serveAccounts([livret, courant, row({ id: 3, name: "Zeta", type: "epargne" })])
    const { user } = view()
    await screen.findAllByText("Livret perso")

    // Principal d'abord, quel que soit le tri
    expect(names()).toEqual(["Compte joint", "Livret perso", "Zeta"])
    await user.click(screen.getByRole("columnheader", { name: /Nom/ }))
    expect(names()).toEqual(["Compte joint", "Zeta", "Livret perso"])
  })

  it("le tri sur une autre colonne repart en croissant", async () => {
    serveAccounts([livret, courant, row({ id: 3, name: "Zeta", type: "epargne", institution: "AXA" })])
    const { user } = view()
    await screen.findAllByText("Livret perso")

    await user.click(screen.getByRole("columnheader", { name: /Établissement/ }))

    expect(names()).toEqual(["Compte joint", "Zeta", "Livret perso"])
  })

  it("comptes archivés : replier/déplier, puis réactivation (PATCH active)", async () => {
    const state = serveAccounts([livret, row({ id: 5, name: "Ancien compte", active: false })])
    const { user } = view()

    await user.click(await screen.findByRole("button", { name: "Comptes archivés (1)" }))
    expect(screen.getByText("Ancien compte")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /Réactiver/ }))

    await waitFor(() => expect(state.writes).toEqual([{ method: "PATCH", path: "/accounts/5", body: { active: true } }]))
    expect(await screen.findByText("Compte réactivé")).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole("button", { name: /Comptes archivés/ })).not.toBeInTheDocument())
  })
})

describe("page Comptes : actions", () => {
  it("favori : PATCH is_main inversé, message selon le sens", async () => {
    const state = serveAccounts([livret, courant])
    const { user } = view()
    await screen.findAllByText("Livret perso")

    const favorites = screen.getAllByRole("button", { name: "Favori" })
    await user.click(favorites[1]) // « Livret perso » : pas encore principal
    await waitFor(() => expect(state.writes).toContainEqual({ method: "PATCH", path: "/accounts/1", body: { is_main: true } }))
    expect(await screen.findByText("Compte défini comme principal")).toBeInTheDocument()

    await user.click(screen.getAllByRole("button", { name: "Favori" })[0])
    await waitFor(() => expect(state.writes).toContainEqual({ method: "PATCH", path: "/accounts/2", body: { is_main: false } }))
    expect(await screen.findByText("Compte retiré des favoris")).toBeInTheDocument()
  })

  it("favori refusé : message d'erreur", async () => {
    serveAccounts([livret])
    server.use(http.patch(apiUrl("/accounts/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view()
    await screen.findAllByText("Livret perso")

    await user.click(screen.getAllByRole("button", { name: "Favori" })[0])

    expect(await screen.findByText("Erreur lors de la modification")).toBeInTheDocument()
  })

  it("archivage confirmé : DELETE, le compte quitte la liste ; refusé : rien n'est envoyé", async () => {
    const state = serveAccounts([livret, courant])
    const { user } = view()
    await screen.findAllByText("Livret perso")

    await user.click(screen.getAllByRole("button", { name: "Archiver" })[1])
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))
    expect(state.writes).toEqual([])

    await user.click(screen.getAllByRole("button", { name: "Archiver" })[1])
    const dialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(dialog).toHaveTextContent("Archiver ce compte ?")
    await user.click(within(dialog).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(state.writes).toEqual([{ method: "DELETE", path: "/accounts/1", body: null }]))
    expect(await screen.findByText("Compte archivé")).toBeInTheDocument()
    await waitFor(() => expect(screen.queryAllByText("Livret perso")).toHaveLength(0))
  })
})

describe("page Comptes : création", () => {
  async function openCreate() {
    const view_ = view()
    await screen.findAllByText("Livret perso")
    await view_.user.click(screen.getByRole("button", { name: "Ajouter un compte" }))
    return { ...view_, dialog: await screen.findByRole("dialog", { name: "Nouveau compte" }) }
  }

  it("nom vide : message, aucune requête", async () => {
    const state = serveAccounts([livret])
    const { user, dialog } = await openCreate()

    await user.click(within(dialog).getByRole("button", { name: "Créer" }))

    expect(await screen.findByText("Le nom du compte est requis")).toBeInTheDocument()
    expect(state.writes).toEqual([])
  })

  it("compte courant : POST avec les valeurs saisies, formulaire fermé, liste rechargée", async () => {
    const state = serveAccounts([livret])
    const { user, dialog } = await openCreate()

    await user.type(within(dialog).getByLabelText("Nom du compte"), "Compte pro")
    await user.type(within(dialog).getByLabelText("Établissement / Banque"), "Fortuneo")
    await user.click(within(dialog).getByRole("button", { name: "Créer" }))

    await waitFor(() => expect(state.writes).toHaveLength(1))
    expect(state.writes[0]).toEqual({
      method: "POST",
      path: "/accounts",
      body: {
        name: "Compte pro", type: "courant", currency: "EUR", institution: "Fortuneo", logo: null,
        asset_class: null, sector: null, geographic_zone: null, valuation_mode: "positions",
        tax_wrapper: null, opened_at: null, fonds_euros_pct: null, fonds_investis_pct: null,
      },
    })
    expect(await screen.findByText("Compte créé avec succès")).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Nouveau compte" })).not.toBeInTheDocument())
    expect((await screen.findAllByText("Compte pro")).length).toBeGreaterThan(0)
  })

  it("assurance-vie : les deux pourcentages se complètent à 100 et partent dans le corps", async () => {
    const state = serveAccounts([livret])
    const { user, dialog } = await openCreate()

    await user.type(within(dialog).getByLabelText("Nom du compte"), "AV Linxea")
    // Le premier combobox est le sélecteur de logo, le deuxième le type
    await user.click(within(dialog).getAllByRole("combobox")[1])
    await user.click(await screen.findByRole("option", { name: "Assurance-Vie" }))
    const euros = await within(dialog).findByLabelText("Fonds Euros (%)")
    await user.type(euros, "60")

    expect(within(dialog).getByLabelText("Fonds Investis (%)")).toHaveValue(40)
    await user.click(within(dialog).getByRole("button", { name: "Créer" }))

    await waitFor(() => expect(state.writes).toHaveLength(1))
    expect(state.writes[0].body).toMatchObject({ type: "assurance_vie", valuation_mode: "snapshot", fonds_euros_pct: 60, fonds_investis_pct: 40 })
  })

  it("création refusée : message d'erreur, formulaire conservé", async () => {
    serveAccounts([livret])
    server.use(http.post(apiUrl("/accounts"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user, dialog } = await openCreate()

    await user.type(within(dialog).getByLabelText("Nom du compte"), "Compte pro")
    await user.click(within(dialog).getByRole("button", { name: "Créer" }))

    expect(await screen.findByText("Erreur lors de la création du compte")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Nouveau compte" })).toBeInTheDocument()
  })
})

describe("page Comptes : modification", () => {
  async function openEdit(accounts: Row[]) {
    const state = serveAccounts(accounts)
    const view_ = view()
    await screen.findAllByText("Livret perso")
    const target = screen.getAllByRole("row").find((r) => within(r).queryByText("Livret perso"))!
    await view_.user.click(within(target).getByRole("button", { name: "Modifier" }))
    return { state, ...view_, dialog: await screen.findByRole("dialog", { name: "Modifier le compte" }) }
  }

  it("renomme : PATCH avec tous les champs du compte, puis liste rechargée", async () => {
    const { state, user, dialog } = await openEdit([livret])

    const name = within(dialog).getByLabelText("Nom du compte")
    await user.clear(name)
    await user.type(name, "Livret A")
    await user.click(within(dialog).getByRole("button", { name: /Enregistrer|Mettre à jour|Sauvegarder/ }))

    await waitFor(() => expect(state.writes).toHaveLength(1))
    expect(state.writes[0]).toMatchObject({ method: "PATCH", path: "/accounts/1", body: { name: "Livret A", type: "epargne", currency: "EUR", institution: "BRED", valuation_mode: "positions", fonds_euros_pct: null } })
    expect(await screen.findByText("Compte mis à jour")).toBeInTheDocument()
    expect((await screen.findAllByText("Livret A")).length).toBeGreaterThan(0)
  })

  it("logo ajouté : appliqué aux autres comptes de la même banque qui n'en ont pas", async () => {
    const other = row({ id: 7, name: "Zeta", type: "courant", institution: "bred", logo: null })
    const { state, user, dialog } = await openEdit([{ ...livret, logo: "bred" }, other, { ...courant, logo: "deja" }])

    await user.click(within(dialog).getByRole("button", { name: /Enregistrer|Mettre à jour|Sauvegarder/ }))

    await waitFor(() => expect(state.writes.length).toBeGreaterThan(1))
    expect(state.writes.map((w) => w.path)).toEqual(["/accounts/1", "/accounts/7"])
    expect(state.writes[1].body).toEqual({ logo: "bred" })
    expect(await screen.findByText("Compte mis à jour (logo appliqué à 1 autre compte)")).toBeInTheDocument()
  })

  it("modification refusée : message d'erreur", async () => {
    const { user, dialog } = await openEdit([livret])
    server.use(http.patch(apiUrl("/accounts/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))

    await user.click(within(dialog).getByRole("button", { name: /Enregistrer|Mettre à jour|Sauvegarder/ }))

    expect(await screen.findByText("Erreur lors de la mise à jour")).toBeInTheDocument()
  })
})
