/** Page Remboursements : créances à recevoir et soldées, filtre par débiteur, montant attendu, suppression, liaison à une entrée. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import Reimbursements from "@/pages/Reimbursements"
import type { Claim } from "@/types/reimbursements"

const claim = (overrides: Partial<Claim> = {}): Claim => ({
  id: 1, debtor: "Denis", expected_amount: 40, received: 10, remaining: 30, note: null, created_at: "2026-06-11T00:00:00", currency: "EUR",
  expense: { id: 30, account_id: 3, date: "2026-06-10T20:00:00", label: "Restaurant", amount: 100 }, allocations: [], ...overrides,
})
const denis = claim()
const sophie = claim({ id: 2, debtor: "Sophie", expected_amount: 25, received: 0, remaining: 25 })

type Write = { method: string; path: string; body: unknown }

/** Créances en mémoire : le filtre (statut, débiteur) est appliqué comme le ferait le serveur ; les requêtes de liste sont consignées. */
function serve({ open = [denis, sophie], settled = [] as Claim[] } = {}) {
  const writes: Write[] = []
  const lists: string[] = []
  let current = open
  server.use(
    http.get(apiUrl("/reimbursements/claims"), ({ request }) => {
      const url = new URL(request.url)
      lists.push(url.search)
      const base = url.searchParams.get("status") === "settled" ? settled : current
      const debtor = url.searchParams.get("debtor")
      return HttpResponse.json(debtor ? base.filter((c) => c.debtor === debtor) : base)
    }),
    http.get(apiUrl("/reimbursements/summary"), () => HttpResponse.json({ total_due: 55, debtors: [{ debtor: "Denis", claims: 1, due: 30 }, { debtor: "Sophie", claims: 1, due: 25 }] })),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([makeAccount({ id: 3, name: "Compte joint" })])),
    http.patch(apiUrl("/reimbursements/claims/:id"), async ({ request, params }) => { writes.push({ method: "PATCH", path: `/reimbursements/claims/${params.id}`, body: await request.json() }); return HttpResponse.json({}) }),
    http.delete(apiUrl("/reimbursements/claims/:id"), ({ params }) => { writes.push({ method: "DELETE", path: `/reimbursements/claims/${params.id}`, body: null }); current = current.filter((c) => String(c.id) !== params.id); return new HttpResponse(null, { status: 204 }) }),
    http.post(apiUrl("/reimbursements/claims/:id/allocations"), async ({ request, params }) => { writes.push({ method: "POST", path: `/reimbursements/claims/${params.id}/allocations`, body: await request.json() }); return HttpResponse.json({}) }),
  )
  return { writes, lists }
}

const view = () => renderWithProviders(<Reimbursements />, { route: "/reimbursements", auth: true })
/** Les deux créances citent la même dépense : on attend qu'elles soient affichées. */
const ready = () => screen.findAllByText(/Restaurant/)

describe("page Remboursements", () => {
  it("affiche le total dû, les débiteurs et chaque créance avec sa dépense, son compte et le reçu", async () => {
    serve()
    view()

    await ready()
    expect(screen.getByRole("heading", { name: "Remboursements" })).toBeInTheDocument()
    expect(screen.getByText(/55,00/)).toBeInTheDocument()
    expect(screen.getByText("30,00 € · 1 créance")).toBeInTheDocument()
    expect(screen.getAllByText(/Compte joint/).length).toBeGreaterThan(0)
    expect(screen.getByText("10,00 € reçu sur 40,00 €")).toBeInTheDocument()
  })

  it("aucune créance à recevoir : message d'invitation ; onglet « Soldées » vide : autre message", async () => {
    const { lists } = serve({ open: [], settled: [] })
    const { user } = view()
    expect(await screen.findByText(/Personne ne vous doit rien/)).toBeInTheDocument()

    await user.click(screen.getByRole("tab", { name: "Soldées" }))

    expect(await screen.findByText("Aucune créance soldée.")).toBeInTheDocument()
    expect(lists.some((q) => q.includes("status=settled"))).toBe(true)
  })

  it("chargement en échec : message d'erreur", async () => {
    server.use(
      http.get(apiUrl("/reimbursements/claims"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
      http.get(apiUrl("/reimbursements/summary"), () => HttpResponse.json({ total_due: 0, debtors: [] })),
      http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
    )
    view()

    expect(await screen.findByText("Erreur lors du chargement des remboursements")).toBeInTheDocument()
  })

  it("cliquer un débiteur filtre la liste ; le bouton du filtre le retire", async () => {
    const { lists } = serve()
    const { user } = view()
    await ready()

    await user.click(screen.getByRole("button", { name: /^Sophie/ }))
    await waitFor(() => expect(lists[lists.length - 1]).toContain("debtor=Sophie"))
    expect(await screen.findByRole("button", { name: /Retirer le filtre/ })).toBeInTheDocument()
    expect(screen.queryByText("10,00 € reçu sur 40,00 €")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: /Retirer le filtre/ }))
    expect(await screen.findByText("10,00 € reçu sur 40,00 €")).toBeInTheDocument()
  })

  it("montant attendu : dialogue prérempli, PATCH (virgule acceptée), liste rechargée", async () => {
    const { writes } = serve()
    const { user } = view()
    await ready()

    await user.click(screen.getAllByRole("button", { name: "Modifier le montant attendu" })[0])
    const dialog = await screen.findByRole("dialog")
    const input = within(dialog).getByLabelText("Montant attendu")
    expect(input).toHaveValue("40")
    await user.clear(input)
    await user.type(input, "45,5")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "PATCH", path: "/reimbursements/claims/1", body: { expected_amount: 45.5 } }]))
    expect(await screen.findByText("Créance modifiée")).toBeInTheDocument()
  })

  it("montant attendu invalide : message, aucune requête ; refus serveur : message du serveur", async () => {
    const { writes } = serve()
    const { user } = view()
    await ready()
    await user.click(screen.getAllByRole("button", { name: "Modifier le montant attendu" })[0])
    const dialog = await screen.findByRole("dialog")
    const input = within(dialog).getByLabelText("Montant attendu")

    await user.clear(input)
    await user.type(input, "0")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))
    expect(await screen.findByText("Le montant doit être un nombre supérieur à 0")).toBeInTheDocument()
    expect(writes).toEqual([])

    server.use(http.patch(apiUrl("/reimbursements/claims/:id"), () => HttpResponse.json({ detail: "Inférieur au montant reçu" }, { status: 422 })))
    await user.clear(input)
    await user.type(input, "5")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))
    expect(await screen.findByText("Inférieur au montant reçu")).toBeInTheDocument()
  })

  it("suppression : confirmation, DELETE, la créance disparaît ; annuler n'envoie rien", async () => {
    const { writes } = serve()
    const { user } = view()
    await ready()

    await user.click(screen.getAllByRole("button", { name: "Supprimer la créance" })[0])
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))
    expect(writes).toEqual([])

    await user.click(screen.getAllByRole("button", { name: "Supprimer la créance" })[0])
    const dialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(dialog).toHaveTextContent("Supprimer la créance de Denis ?")
    await user.click(within(dialog).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "DELETE", path: "/reimbursements/claims/1", body: null }]))
    expect(await screen.findByText("Créance supprimée")).toBeInTheDocument()
  })

  it("suppression refusée : message d'échec", async () => {
    serve()
    server.use(http.delete(apiUrl("/reimbursements/claims/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view()
    await ready()

    await user.click(screen.getAllByRole("button", { name: "Supprimer la créance" })[0])
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Échec de la suppression")).toBeInTheDocument()
  })

  it("lier un remboursement : candidates proposées, POST de l'entrée choisie, liste rechargée", async () => {
    const { writes, lists } = serve()
    server.use(http.get(apiUrl("/reimbursements/claims/:id/candidates"), () => HttpResponse.json([
      { id: 70, account_id: 3, date: "2026-06-20T10:00:00", label: "Virement Denis", amount: 30, available: 30, day_gap: 10, debtor_match: true },
    ])))
    const { user } = view()
    await ready()
    const before = lists.length

    await user.click(screen.getAllByRole("button", { name: "Lier un remboursement" })[0])
    const dialog = await screen.findByRole("dialog", { name: "Lier un remboursement" })
    expect(await within(dialog).findByText("Virement Denis")).toBeInTheDocument()
    expect(within(dialog).getByText("Débiteur reconnu")).toBeInTheDocument()
    await user.click(within(dialog).getByRole("button", { name: "Lier" }))

    await waitFor(() => expect(writes).toEqual([{ method: "POST", path: "/reimbursements/claims/1/allocations", body: { entree_id: 70 } }]))
    expect(await screen.findByText("Remboursement lié")).toBeInTheDocument()
    await waitFor(() => expect(lists.length).toBeGreaterThan(before))
  })

  it("aucune candidate : message ; recherche en échec : message d'erreur", async () => {
    serve()
    server.use(http.get(apiUrl("/reimbursements/claims/:id/candidates"), () => HttpResponse.json([])))
    const { user } = view()
    await ready()

    await user.click(screen.getAllByRole("button", { name: "Lier un remboursement" })[0])

    expect(await screen.findByText(/Aucune entrée disponible entre 7 jours avant/)).toBeInTheDocument()
  })

  it("une créance entièrement reçue n'a pas de bouton « Lier un remboursement »", async () => {
    serve({ open: [claim({ id: 3, debtor: "Paul", received: 40, remaining: 0 })] })
    view()
    await ready()

    expect(screen.queryByRole("button", { name: "Lier un remboursement" })).not.toBeInTheDocument()
  })
})
