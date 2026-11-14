/** Édition d'une transaction depuis le Centre d'Actions : corps du PATCH, garde-fous du bouton, suppression confirmée. */
import { screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { makeAccount, makeTransaction } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { TransactionEditor } from "@/pages/Audit/TransactionEditor"

const account = makeAccount({ id: 1, name: "Compte courant" })
const courses = { id: 3, name: "Courses", type: "depense" }
const tx = makeTransaction({ id: 11, account_id: 1, merchant: "Carrefour", amount: 42.5, category_id: 3, date: "2026-06-15T10:00:00" })

/** Le composant rend une version mobile et une version bureau (masquée en CSS) : on pilote la première. */
const first = (nodes: HTMLElement[]) => nodes[0]

function setup(props: Partial<React.ComponentProps<typeof TransactionEditor>> = {}) {
  const onSaved = vi.fn()
  const onDeleted = vi.fn()
  const view = renderWithProviders(
    <TransactionEditor tx={tx} categories={[courses]} accounts={[account]} onSaved={onSaved} onDeleted={onDeleted} {...props} />,
    { auth: true },
  )
  return { onSaved, onDeleted, ...view }
}

describe("TransactionEditor", () => {
  it("affiche le compte, le marchand et le montant de la transaction", () => {
    setup()

    expect(screen.getAllByText("Compte courant").length).toBeGreaterThan(0)
    expect(first(screen.getAllByDisplayValue("Carrefour"))).toBeInTheDocument()
    expect(first(screen.getAllByDisplayValue("42.5"))).toBeInTheDocument()
  })

  it("compte inconnu : affiche son identifiant", () => {
    setup({ accounts: [] })

    expect(screen.getAllByText("ID: 1").length).toBeGreaterThan(0)
  })

  it("enregistre : PATCH avec le marchand et le montant corrigés, puis onSaved avec la réponse", async () => {
    let body: Record<string, unknown> | undefined
    const saved = { ...tx, merchant: "Carrefour City", amount: 50 }
    server.use(
      http.patch(apiUrl("/transactions/11"), async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(saved)
      }),
    )
    const { user, onSaved } = setup()

    const merchant = first(screen.getAllByDisplayValue("Carrefour"))
    await user.clear(merchant)
    await user.type(merchant, "Carrefour City")
    const amount = first(screen.getAllByDisplayValue("42.5"))
    await user.clear(amount)
    await user.type(amount, "50")
    await user.click(first(screen.getAllByRole("button", { name: "Enregistrer" })))

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(saved))
    expect(body).toMatchObject({ merchant: "Carrefour City", amount: 50, category_id: 3, type: "Sortie", note: null })
    expect(body?.date).toBe("2026-06-15T10:00:00")
    expect(await screen.findByText("Transaction enregistrée")).toBeInTheDocument()
  })

  it("une note saisie (version bureau) part dans le PATCH, rognée", async () => {
    let body: Record<string, unknown> | undefined
    server.use(
      http.patch(apiUrl("/transactions/11"), async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(tx)
      }),
    )
    const { user } = setup()

    await user.type(screen.getByPlaceholderText("Note"), "  remboursé  ")
    await user.click(first(screen.getAllByRole("button", { name: "Enregistrer" })))

    await waitFor(() => expect(body).toBeDefined())
    expect(body?.note).toBe("remboursé")
  })

  it("« Enregistrer » est désactivé sans marchand ou avec un montant nul", async () => {
    const { user } = setup()
    const save = first(screen.getAllByRole("button", { name: "Enregistrer" }))
    expect(save).toBeEnabled()

    await user.clear(first(screen.getAllByDisplayValue("Carrefour")))
    expect(save).toBeDisabled()

    await user.type(first(screen.getAllByPlaceholderText("Marchand")), "Lidl")
    expect(save).toBeEnabled()

    const amount = first(screen.getAllByDisplayValue("42.5"))
    await user.clear(amount)
    await user.type(amount, "0")
    expect(save).toBeDisabled()
  })

  it("échec de l'enregistrement : message d'erreur, onSaved non appelé", async () => {
    server.use(http.patch(apiUrl("/transactions/11"), () => HttpResponse.json({ detail: "Compte verrouillé" }, { status: 400 })))
    const { user, onSaved } = setup()

    await user.click(first(screen.getAllByRole("button", { name: "Enregistrer" })))

    expect(await screen.findByText("Compte verrouillé")).toBeInTheDocument()
    expect(onSaved).not.toHaveBeenCalled()
  })

  it("suppression confirmée : DELETE puis onDeleted avec l'identifiant", async () => {
    let deleted = false
    server.use(
      http.delete(apiUrl("/transactions/11"), () => {
        deleted = true
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { user, onDeleted } = setup()

    await user.click(first(screen.getAllByRole("button", { name: "Supprimer" })))
    const dialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(dialog).toHaveTextContent("Supprimer la transaction « Carrefour »")
    await user.click(within(dialog).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(onDeleted).toHaveBeenCalledWith(11))
    expect(deleted).toBe(true)
    expect(await screen.findByText("Transaction supprimée")).toBeInTheDocument()
  })

  it("suppression annulée : aucune requête, onDeleted non appelé", async () => {
    let deleted = false
    server.use(http.delete(apiUrl("/transactions/11"), () => { deleted = true; return new HttpResponse(null, { status: 204 }) }))
    const { user, onDeleted } = setup()

    await user.click(first(screen.getAllByRole("button", { name: "Supprimer" })))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))

    expect(deleted).toBe(false)
    expect(onDeleted).not.toHaveBeenCalled()
  })

  it("échec de la suppression : message d'erreur, onDeleted non appelé", async () => {
    server.use(http.delete(apiUrl("/transactions/11"), () => HttpResponse.json({ detail: "Transaction liée" }, { status: 409 })))
    const { user, onDeleted } = setup()

    await user.click(first(screen.getAllByRole("button", { name: "Supprimer" })))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Transaction liée")).toBeInTheDocument()
    expect(onDeleted).not.toHaveBeenCalled()
  })

  it("sans onDeleted : pas de bouton « Supprimer »", () => {
    setup({ onDeleted: undefined })

    expect(screen.queryByRole("button", { name: "Supprimer" })).not.toBeInTheDocument()
  })
})
