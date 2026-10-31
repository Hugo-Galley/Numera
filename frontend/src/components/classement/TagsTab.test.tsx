/** Tags : liste, création, modification, archivage, suppression confirmée. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { TagsTab } from "./TagsTab"

interface Tag {
  id: number
  name: string
  color: string | null
  archived?: boolean
}

/** Tags en mémoire : POST ajoute, PATCH fusionne, DELETE retire ; les écritures sont consignées. */
function serveTags(initial: Tag[] = []) {
  const state = { tags: [...initial], writes: [] as { method: string; path: string; body: unknown }[] }
  server.use(
    http.get(apiUrl("/tags"), () => HttpResponse.json(state.tags)),
    http.post(apiUrl("/tags"), async ({ request }) => {
      const body = (await request.json()) as Omit<Tag, "id">
      state.writes.push({ method: "POST", path: "/tags", body })
      state.tags.push({ id: 60, ...body })
      return HttpResponse.json({ id: 60, ...body })
    }),
    http.patch(apiUrl("/tags/:id"), async ({ request, params }) => {
      const body = (await request.json()) as Partial<Tag>
      state.writes.push({ method: "PATCH", path: `/tags/${params.id}`, body })
      state.tags = state.tags.map((t) => (String(t.id) === params.id ? { ...t, ...body } : t))
      return HttpResponse.json({})
    }),
    http.delete(apiUrl("/tags/:id"), ({ params }) => {
      state.writes.push({ method: "DELETE", path: `/tags/${params.id}`, body: null })
      state.tags = state.tags.filter((t) => String(t.id) !== params.id)
      return new HttpResponse(null, { status: 204 })
    }),
  )
  return state
}

const VACANCES: Tag = { id: 1, name: "Vacances", color: "#10b981", archived: false }

describe("TagsTab", () => {
  it("chargement puis liste", async () => {
    serveTags([VACANCES])
    renderWithProviders(<TagsTab />, { auth: true })

    expect(screen.getByText("Chargement de vos tags...")).toBeInTheDocument()
    expect(await screen.findByText("Vacances")).toBeInTheDocument()
  })

  it("aucun tag : état vide", async () => {
    serveTags()
    renderWithProviders(<TagsTab />, { auth: true })

    expect(await screen.findByText("Aucun tag créé pour le moment.")).toBeInTheDocument()
  })

  it("échec du chargement : alerte avec « Réessayer », jamais l'état vide", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined)
    serveTags([VACANCES])
    server.use(http.get(apiUrl("/tags"), () => HttpResponse.json({ detail: "boom" }, { status: 500 }), { once: true }))
    const { user } = renderWithProviders(<TagsTab />, { auth: true })

    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible de charger les tags.")
    expect(screen.queryByText("Aucun tag créé pour le moment.")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Réessayer" }))
    expect(await screen.findByText("Vacances")).toBeInTheDocument()
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("création : nom et couleur choisie envoyés, toast, tag ajouté à la liste", async () => {
    const state = serveTags()
    const { user } = renderWithProviders(<TagsTab />, { auth: true })
    await screen.findByText("Aucun tag créé pour le moment.")

    await user.click(screen.getByRole("button", { name: "Nouveau tag" }))
    const dialog = screen.getByRole("dialog", { name: "Nouveau tag" })
    await user.type(within(dialog).getByLabelText("Nom"), "Travaux")
    await user.click(within(dialog).getByTitle("Amber"))
    await user.click(within(dialog).getByRole("button", { name: "Créer le tag" }))

    expect(await screen.findByText("Tag ajouté")).toBeInTheDocument()
    expect(state.writes).toEqual([{ method: "POST", path: "/tags", body: { name: "Travaux", color: "#f59e0b" } }])
    expect(await screen.findByText("Travaux")).toBeInTheDocument()
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("sans nom : rien n'est envoyé", async () => {
    const state = serveTags()
    const { user } = renderWithProviders(<TagsTab />, { auth: true })
    await screen.findByText("Aucun tag créé pour le moment.")

    await user.click(screen.getByRole("button", { name: "Nouveau tag" }))
    await user.click(screen.getByRole("button", { name: "Créer le tag" }))

    expect(state.writes).toEqual([])
    expect(screen.getByRole("dialog", { name: "Nouveau tag" })).toBeInTheDocument()
  })

  it("modification : dialogue prérempli, PATCH nom + couleur", async () => {
    const state = serveTags([VACANCES])
    const { user } = renderWithProviders(<TagsTab />, { auth: true })
    await screen.findByText("Vacances")

    await user.click(screen.getByRole("button", { name: "Modifier" }))
    const dialog = screen.getByRole("dialog", { name: "Modifier le tag" })
    expect(within(dialog).getByLabelText("Nom")).toHaveValue("Vacances")
    await user.clear(within(dialog).getByLabelText("Nom"))
    await user.type(within(dialog).getByLabelText("Nom"), "Été 2026")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer les modifications" }))

    expect(await screen.findByText("Tag mis à jour")).toBeInTheDocument()
    expect(state.writes).toEqual([{ method: "PATCH", path: "/tags/1", body: { name: "Été 2026", color: "#10b981" } }])
    expect(await screen.findByText("Été 2026")).toBeInTheDocument()
  })

  it("archiver : PATCH archived, bouton « Réactiver » ensuite", async () => {
    const state = serveTags([VACANCES])
    const { user } = renderWithProviders(<TagsTab />, { auth: true })
    await screen.findByText("Vacances")

    await user.click(screen.getByRole("button", { name: "Archiver" }))

    expect(await screen.findByText("Tag archivé : masqué des sélecteurs, transactions inchangées")).toBeInTheDocument()
    expect(state.writes).toEqual([{ method: "PATCH", path: "/tags/1", body: { archived: true } }])
    expect(await screen.findByRole("button", { name: "Réactiver" })).toBeInTheDocument()
  })

  it("suppression confirmée : message explicite, DELETE, toast, tag retiré", async () => {
    const state = serveTags([VACANCES])
    const { user } = renderWithProviders(<TagsTab />, { auth: true })
    await screen.findByText("Vacances")

    await user.click(screen.getByRole("button", { name: "Supprimer" }))
    const confirmDialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(confirmDialog).toHaveTextContent("Supprimer ce tag ? Il sera retiré de toutes les transactions.")
    await user.click(within(confirmDialog).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Tag supprimé")).toBeInTheDocument()
    expect(state.writes).toEqual([{ method: "DELETE", path: "/tags/1", body: null }])
    await waitFor(() => expect(screen.queryByText("Vacances")).not.toBeInTheDocument())
  })

  it("suppression annulée : aucune requête", async () => {
    const state = serveTags([VACANCES])
    const { user } = renderWithProviders(<TagsTab />, { auth: true })
    await screen.findByText("Vacances")

    await user.click(screen.getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    expect(state.writes).toEqual([])
  })

  it("suppression en échec : toast, tag conservé", async () => {
    serveTags([VACANCES])
    server.use(http.delete(apiUrl("/tags/:id"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))
    const { user } = renderWithProviders(<TagsTab />, { auth: true })
    await screen.findByText("Vacances")

    await user.click(screen.getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Erreur lors de la suppression")).toBeInTheDocument()
    expect(screen.getByText("Vacances")).toBeInTheDocument()
  })
})
