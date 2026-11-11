/** Créances existantes d'une dépense (renommer, supprimer) et affectation d'une entrée à une créance ouverte. */
import { screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { ReimbursementDialog } from "@/components/reimbursements/ReimbursementDialog"
import type { Claim, EntryClaims } from "@/types/reimbursements"

const expenseRef = { id: 30, account_id: 1, date: "2026-06-10T20:00:00", label: "Restaurant", amount: 100 }
const claim = (overrides: Partial<Claim> = {}): Claim => ({
  id: 1, debtor: "Denis", expected_amount: 40, received: 10, remaining: 30, note: null, created_at: "2026-06-11T00:00:00", currency: "EUR",
  expense: expenseRef, allocations: [{ id: 5, entree_id: 70, amount: 10, date: "2026-06-12T00:00:00", label: "Virement Denis", account_id: 1 }], ...overrides,
})

const expense = { id: 30, type: "Sortie", merchant: "Restaurant", date: "2026-06-10T20:00:00", amount: 100, currency: "EUR" }
const entree = { id: 70, type: "Entree", merchant: "Virement Sécu", date: "2026-06-20T10:00:00", amount: 50, currency: "EUR" }

type Write = { method: string; path: string; body: unknown }

function serve({ claims = [claim()], entry }: { claims?: Claim[]; entry?: EntryClaims } = {}) {
  const writes: Write[] = []
  const note = async (request: Request, path: string) => {
    const text = await request.text()
    writes.push({ method: request.method, path, body: text ? JSON.parse(text) : null })
  }
  server.use(
    http.get(apiUrl("/reimbursements/claims"), () => HttpResponse.json(claims)),
    http.get(apiUrl("/reimbursements/entries/:id/claims"), () => HttpResponse.json(entry)),
    http.patch(apiUrl("/reimbursements/claims/:id"), async ({ request, params }) => { await note(request, `/reimbursements/claims/${params.id}`); return HttpResponse.json({}) }),
    http.delete(apiUrl("/reimbursements/claims/:id"), async ({ request, params }) => { await note(request, `/reimbursements/claims/${params.id}`); return new HttpResponse(null, { status: 204 }) }),
    http.post(apiUrl("/reimbursements/claims/:id/allocations"), async ({ request, params }) => { await note(request, `/reimbursements/claims/${params.id}/allocations`); return HttpResponse.json({}) }),
    http.delete(apiUrl("/reimbursements/allocations/:id"), async ({ request, params }) => { await note(request, `/reimbursements/allocations/${params.id}`); return new HttpResponse(null, { status: 204 }) }),
  )
  return writes
}

function setup(transaction = expense) {
  const onDone = vi.fn()
  const view = renderWithProviders(<ReimbursementDialog open transaction={transaction} onOpenChange={vi.fn()} onDone={onDone} />, { auth: true })
  return { onDone, ...view }
}

describe("ReimbursementDialog : créances d'une dépense", () => {
  it("liste les créances avec reçu / attendu, les affectations et le total déclaré", async () => {
    serve()
    setup()

    expect(await screen.findByDisplayValue("Denis")).toBeInTheDocument()
    expect(screen.getByText(/Virement Denis/)).toBeInTheDocument()
    expect(screen.getByText(/Déclaré :/)).toHaveTextContent("40,00")
  })

  it("renommer le débiteur (à la sortie du champ) : PATCH avec le nom rogné", async () => {
    const writes = serve()
    const { user, onDone } = setup()
    const input = await screen.findByDisplayValue("Denis")

    await user.clear(input)
    await user.type(input, "  Denis Martin ")
    await user.tab()

    await waitFor(() => expect(writes).toEqual([{ method: "PATCH", path: "/reimbursements/claims/1", body: { debtor: "Denis Martin" } }]))
    expect(await screen.findByText("Débiteur renommé")).toBeInTheDocument()
    // Renommer ne change pas les totaux : le parent n'est pas prévenu
    expect(onDone).not.toHaveBeenCalled()
  })

  it("nom inchangé ou vidé : aucune requête", async () => {
    const writes = serve()
    const { user } = setup()
    const input = await screen.findByDisplayValue("Denis")

    await user.click(input)
    await user.tab()
    await user.clear(input)
    await user.tab()

    expect(writes).toEqual([])
  })

  it("renommage refusé : message d'erreur du serveur", async () => {
    serve()
    server.use(http.patch(apiUrl("/reimbursements/claims/:id"), () => HttpResponse.json({ detail: "Nom déjà utilisé" }, { status: 409 })))
    const { user } = setup()
    const input = await screen.findByDisplayValue("Denis")

    await user.type(input, " 2")
    await user.tab()

    expect(await screen.findByText("Nom déjà utilisé")).toBeInTheDocument()
  })

  it("supprimer une créance : confirmation, DELETE, parent prévenu ; annuler n'envoie rien", async () => {
    const writes = serve()
    const { user, onDone } = setup()
    await screen.findByDisplayValue("Denis")

    await user.click(screen.getByRole("button", { name: "Supprimer la créance" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))
    expect(writes).toEqual([])

    await user.click(screen.getByRole("button", { name: "Supprimer la créance" }))
    const confirmDialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(confirmDialog).toHaveTextContent("Supprimer la créance de Denis ?")
    await user.click(within(confirmDialog).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "DELETE", path: "/reimbursements/claims/1", body: null }]))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(await screen.findByText("Créance supprimée")).toBeInTheDocument()
  })

  it("suppression refusée : message d'erreur, parent non prévenu", async () => {
    serve()
    server.use(http.delete(apiUrl("/reimbursements/claims/:id"), () => HttpResponse.json({ detail: "Créance déjà soldée" }, { status: 409 })))
    const { user, onDone } = setup()
    await screen.findByDisplayValue("Denis")

    await user.click(screen.getByRole("button", { name: "Supprimer la créance" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Créance déjà soldée")).toBeInTheDocument()
    expect(onDone).not.toHaveBeenCalled()
  })

  it("chargement en échec : message d'erreur", async () => {
    server.use(http.get(apiUrl("/reimbursements/claims"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    setup()

    expect(await screen.findByText("Erreur lors du chargement des remboursements")).toBeInTheDocument()
  })
})

describe("ReimbursementDialog : entrée à affecter", () => {
  const open = claim({ id: 2, debtor: "Sécu", expected_amount: 80, received: 0, remaining: 80, allocations: [] })
  const entry: EntryClaims = {
    entree_id: 70, amount: 50, available: 30, open_claims: [open],
    allocations: [{ id: 9, claim_id: 1, amount: 20, debtor: "Denis" }],
  }

  it("affiche le montant disponible, les affectations existantes et les créances ouvertes", async () => {
    serve({ entry })
    setup(entree)

    expect(await screen.findByText("Sécu")).toBeInTheDocument()
    expect(screen.getByText(/Disponible :/)).toHaveTextContent("30,00")
    expect(screen.getByText(/Affecté à Denis/)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Affecter un remboursement" })).toBeInTheDocument()
  })

  it("« Affecter » sans montant : POST avec l'entrée seule (le serveur prend le maximum possible)", async () => {
    const writes = serve({ entry })
    const { user, onDone } = setup(entree)
    await screen.findByText("Sécu")

    await user.click(screen.getByRole("button", { name: "Affecter" }))

    await waitFor(() => expect(writes).toEqual([{ method: "POST", path: "/reimbursements/claims/2/allocations", body: { entree_id: 70 } }]))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(await screen.findByText("Remboursement affecté à Sécu")).toBeInTheDocument()
  })

  it("« Affecter » avec un montant (virgule) : POST avec ce montant", async () => {
    const writes = serve({ entry })
    const { user } = setup(entree)
    await screen.findByText("Sécu")

    await user.type(screen.getByPlaceholderText("30"), "12,5")
    await user.click(screen.getByRole("button", { name: "Affecter" }))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].body).toEqual({ entree_id: 70, amount: 12.5 })
  })

  it("rien de disponible : « Affecter » est désactivé", async () => {
    serve({ entry: { ...entry, available: 0 } })
    setup(entree)
    await screen.findByText("Sécu")

    expect(screen.getByRole("button", { name: "Affecter" })).toBeDisabled()
  })

  it("affectation refusée : message d'erreur du serveur", async () => {
    serve({ entry })
    server.use(http.post(apiUrl("/reimbursements/claims/:id/allocations"), () => HttpResponse.json({ detail: "Montant supérieur au disponible" }, { status: 422 })))
    const { user, onDone } = setup(entree)
    await screen.findByText("Sécu")

    await user.click(screen.getByRole("button", { name: "Affecter" }))

    expect(await screen.findByText("Montant supérieur au disponible")).toBeInTheDocument()
    expect(onDone).not.toHaveBeenCalled()
  })

  it("« Retirer » une affectation : DELETE, parent prévenu", async () => {
    const writes = serve({ entry })
    const { user, onDone } = setup(entree)
    await screen.findByText("Sécu")

    await user.click(screen.getByRole("button", { name: "Retirer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "DELETE", path: "/reimbursements/allocations/9", body: null }]))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(await screen.findByText("Affectation retirée")).toBeInTheDocument()
  })

  it("aucune créance ouverte : message qui renvoie vers la dépense", async () => {
    serve({ entry: { ...entry, open_claims: [], allocations: [] } })
    setup(entree)

    expect(await screen.findByText(/Aucune créance ouverte/)).toBeInTheDocument()
  })
})
