/** Revue des virements internes : suggestions (lier, ignorer, recherche avec tolérances) et virements déjà liés (délier). */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { TransferReview } from "@/components/audit/TransferReview"
import type { LinkedTransfer, PotentialTransfer } from "@/types/transfers"

const courant = makeAccount({ id: 1, name: "Compte courant" })
const livret = makeAccount({ id: 2, name: "Livret A", type: "epargne" })

const PAIR: PotentialTransfer = {
  sortie: { id: 10, account_id: 1, merchant: "VIR LIVRET", date: "2026-06-10T09:00:00", amount: 200, currency: "EUR" },
  entree: { id: 11, account_id: 2, merchant: "Versement", date: "2026-06-11T09:00:00", amount: 200, currency: "EUR" },
  type: "regular",
  confidence: "high",
  ambiguous: false,
  day_gap: 1,
}

const LINKED: LinkedTransfer = { id: 20, account_id: 1, merchant: "Épargne mensuelle", date: "2026-05-02T08:00:00", amount: 150, currency: "EUR", type: "Sortie", link_origin: "rule", linked_account_id: 2 }

/** Serveur en mémoire : chaque écriture est consignée (méthode, chemin avec query, corps). */
function serveTransfers({ potentials = [PAIR], linked = [LINKED] }: { potentials?: PotentialTransfer[]; linked?: LinkedTransfer[] } = {}) {
  const state = { writes: [] as string[], suggestionQueries: [] as string[], loads: 0 }
  const write = (request: Request) => state.writes.push(`${request.method} ${new URL(request.url).pathname.replace(/^\/api/, "")}${new URL(request.url).search}`)
  server.use(
    http.get(apiUrl("/transactions/potential-transfers"), ({ request }) => {
      state.loads += 1
      state.suggestionQueries.push(new URL(request.url).search)
      return HttpResponse.json(potentials)
    }),
    http.get(apiUrl("/transactions"), () => HttpResponse.json(linked)),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([courant, livret])),
    http.post(apiUrl("/transactions/:id/link/:other"), ({ request }) => { write(request); return HttpResponse.json({}) }),
    http.post(apiUrl("/transactions/:id/ignore"), ({ request }) => { write(request); return new HttpResponse(null, { status: 204 }) }),
    http.post(apiUrl("/transactions/:id/unlink"), ({ request }) => { write(request); return new HttpResponse(null, { status: 204 }) }),
  )
  return state
}

const view = () => renderWithProviders(<TransferReview />, { auth: true })

describe("TransferReview", () => {
  it("chargement puis suggestions et virements liés avec leurs comptes et leur origine", async () => {
    serveTransfers()
    view()

    expect(screen.getByText("Chargement...")).toBeInTheDocument()
    expect(await screen.findByText("VIR LIVRET")).toBeInTheDocument()
    expect(screen.getByText("Versement")).toBeInTheDocument()
    expect(screen.getByText("Confiance haute")).toBeInTheDocument()
    expect(screen.getByText("Épargne mensuelle")).toBeInTheDocument()
    expect(screen.getByText("Règle")).toBeInTheDocument()
    expect(screen.getAllByText("Livret A").length).toBeGreaterThan(0)
  })

  it("interroge les suggestions avec les tolérances par défaut (5 jours, 1 %)", async () => {
    const state = serveTransfers()
    view()

    await screen.findByText("VIR LIVRET")
    expect(state.suggestionQueries[0]).toBe("?months=0&days_tolerance=5&amount_tolerance_pct=1")
  })

  it("rien à traiter : deux états vides", async () => {
    serveTransfers({ potentials: [], linked: [] })
    view()

    expect(await screen.findByText("Aucune suggestion en attente.")).toBeInTheDocument()
    expect(screen.getByText("Aucun virement lié pour le moment.")).toBeInTheDocument()
  })

  it("plusieurs choix possibles et confiance moyenne : badges distincts", async () => {
    serveTransfers({ potentials: [{ ...PAIR, ambiguous: true }, { ...PAIR, sortie: { ...PAIR.sortie, id: 12 }, entree: { ...PAIR.entree, id: 13 }, confidence: "medium" }], linked: [] })
    view()

    expect(await screen.findByText("Plusieurs choix")).toBeInTheDocument()
    expect(screen.getByText("Moyenne")).toBeInTheDocument()
  })

  it("« Lier » : POST avec la sortie, l'entrée et le type, puis rechargement", async () => {
    const state = serveTransfers()
    const { user } = view()
    await screen.findByText("VIR LIVRET")
    const loads = state.loads

    await user.click(screen.getByRole("button", { name: "Lier" }))

    await waitFor(() => expect(state.writes).toEqual(["POST /transactions/10/link/11?type=regular"]))
    expect(await screen.findByText("Transactions liées avec succès")).toBeInTheDocument()
    await waitFor(() => expect(state.loads).toBeGreaterThan(loads))
  })

  it("« Lier » refusé : message d'échec", async () => {
    serveTransfers()
    server.use(http.post(apiUrl("/transactions/:id/link/:other"), () => HttpResponse.json({ detail: "non" }, { status: 409 })))
    const { user } = view()

    await user.click(await screen.findByRole("button", { name: "Lier" }))

    expect(await screen.findByText("Échec de la liaison")).toBeInTheDocument()
  })

  it("« Ignorer » : POST avec l'autre transaction et le type", async () => {
    const state = serveTransfers()
    const { user } = view()

    await user.click(await screen.findByRole("button", { name: "Ignorer" }))

    await waitFor(() => expect(state.writes).toEqual(["POST /transactions/10/ignore?other_id=11&type=regular"]))
    expect(await screen.findByText("Suggestion ignorée")).toBeInTheDocument()
  })

  it("« Rechercher » applique les tolérances saisies, y compris à un rechargement ultérieur", async () => {
    const state = serveTransfers()
    const { user } = view()
    await screen.findByText("VIR LIVRET")

    const days = screen.getByLabelText("Écart de date (jours)")
    await user.clear(days)
    await user.type(days, "10")
    const tolerance = screen.getByLabelText("Écart de montant (%)")
    await user.clear(tolerance)
    await user.type(tolerance, "2,5")
    await user.click(screen.getByRole("button", { name: "Rechercher" }))

    await waitFor(() => expect(state.suggestionQueries[state.suggestionQueries.length - 1]).toBe("?months=0&days_tolerance=10&amount_tolerance_pct=2.5"))
    // Après une action, les suggestions sont rechargées avec les tolérances appliquées
    await user.click(screen.getByRole("button", { name: "Ignorer" }))
    await waitFor(() => expect(state.suggestionQueries[state.suggestionQueries.length - 1]).toBe("?months=0&days_tolerance=10&amount_tolerance_pct=2.5"))
  })

  it("recherche refusée (tolérance trop large) : message d'échec", async () => {
    serveTransfers()
    const { user } = view()
    await screen.findByText("VIR LIVRET")
    server.use(http.get(apiUrl("/transactions/potential-transfers"), () => HttpResponse.json({ detail: "trop large" }, { status: 422 })))

    // Autre tolérance que l'initiale : la lecture mise en cache ne répond pas à sa place
    const days = screen.getByLabelText("Écart de date (jours)")
    await user.clear(days)
    await user.type(days, "40")
    await user.click(screen.getByRole("button", { name: "Rechercher" }))

    expect(await screen.findByText(/Échec de la recherche/)).toBeInTheDocument()
  })

  it("« Délier » : confirmation puis POST unlink ; annuler n'envoie rien", async () => {
    const state = serveTransfers()
    const { user } = view()
    await user.click(await screen.findByRole("button", { name: "Délier" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Délier le virement" })).getByRole("button", { name: "Annuler" }))
    expect(state.writes).toEqual([])

    await user.click(screen.getByRole("button", { name: "Délier" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Délier le virement" })).getByRole("button", { name: "Délier" }))

    await waitFor(() => expect(state.writes).toEqual(["POST /transactions/20/unlink"]))
    expect(await screen.findByText("Transactions déliées")).toBeInTheDocument()
  })

  it("chargement en échec : message d'erreur", async () => {
    server.use(
      http.get(apiUrl("/transactions/potential-transfers"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
      http.get(apiUrl("/transactions"), () => HttpResponse.json([])),
      http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
    )
    view()

    expect(await screen.findByText("Erreur lors du chargement des virements")).toBeInTheDocument()
  })
})
