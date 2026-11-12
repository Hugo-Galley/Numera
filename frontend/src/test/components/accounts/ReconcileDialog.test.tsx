/** Rapprochement bancaire : solde de la banque comparé à celui de Numera, écart et causes probables. */
import { screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { ReconcileDialog } from "@/components/accounts/ReconcileDialog"

const account = { id: 4, name: "Compte joint", currency: "EUR" }

function setup(response: () => Response | Promise<Response>, props: Partial<React.ComponentProps<typeof ReconcileDialog>> = {}) {
  const posted: unknown[] = []
  server.use(http.post(apiUrl("/accounts/4/reconcile"), async ({ request }) => { posted.push(await request.json()); return response() }))
  const onOpenChange = vi.fn()
  const onVerified = vi.fn()
  const view = renderWithProviders(<ReconcileDialog account={account} open onOpenChange={onOpenChange} onVerified={onVerified} {...props} />, { auth: true })
  return { posted, onOpenChange, onVerified, ...view }
}

const typeBalance = async (user: ReturnType<typeof setup>["user"], value: string) => {
  await user.type(screen.getByLabelText(/Solde banque/), value)
}

describe("ReconcileDialog", () => {
  it("annonce le compte et la devise ; « Vérifier » est désactivé tant qu'aucun solde n'est saisi", () => {
    setup(() => HttpResponse.json({}))

    expect(screen.getByRole("dialog")).toHaveTextContent("Compte joint")
    expect(screen.getByLabelText("Solde banque (EUR)")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Vérifier" })).toBeDisabled()
  })

  it("solde concordant : POST (date du jour, solde à virgule), compte marqué vérifié, parent prévenu", async () => {
    const { user, posted, onVerified } = setup(() => HttpResponse.json({ currency: "EUR", bank_balance: 1234.5, numera_balance: 1234.5, gap: 0, matches: true, verified: true, hints: [] }))

    await typeBalance(user, "1 234,5")
    await user.click(screen.getByRole("button", { name: "Vérifier" }))

    await waitFor(() => expect(onVerified).toHaveBeenCalledTimes(1))
    expect(posted).toHaveLength(1)
    expect(posted[0]).toMatchObject({ bank_balance: 1234.5 })
    expect((posted[0] as { date: string }).date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(await screen.findByText("Solde concordant : compte vérifié")).toBeInTheDocument()
    expect(screen.getByText(/Les soldes concordent au/)).toBeInTheDocument()
  })

  it("écart : soldes banque / Numera, écart signé et causes probables avec leurs transactions", async () => {
    const hint = {
      kind: "duplicate", message: "Une opération semble saisie deux fois",
      transactions: [{ id: 1, date: "2026-06-10T10:00:00", merchant: "Boulangerie", type: "Sortie", amount: 4.5 }, { id: 2, date: "2026-06-11T10:00:00", merchant: "Remboursement", type: "Entree", amount: 20 }],
    }
    const { user, onVerified } = setup(() => HttpResponse.json({ currency: "EUR", bank_balance: 1000, numera_balance: 1004.5, gap: 4.5, matches: false, verified: false, hints: [hint] }))

    await typeBalance(user, "1000")
    await user.click(screen.getByRole("button", { name: "Vérifier" }))

    expect(await screen.findByText("Une opération semble saisie deux fois")).toBeInTheDocument()
    expect(screen.getByText("Banque")).toBeInTheDocument()
    expect(screen.getByText(/\+\s?4,50/)).toBeInTheDocument()
    expect(screen.getByText(/Boulangerie/)).toBeInTheDocument()
    expect(screen.getByText(/-\s4,50/)).toBeInTheDocument()
    expect(screen.getByText(/\+\s20,00/)).toBeInTheDocument()
    expect(onVerified).not.toHaveBeenCalled()
  })

  it("solde illisible : message, aucune requête", async () => {
    const { user, posted } = setup(() => HttpResponse.json({}))

    await typeBalance(user, "abc")
    await user.click(screen.getByRole("button", { name: "Vérifier" }))

    expect(await screen.findByText("Saisissez la date et le solde affiché par la banque")).toBeInTheDocument()
    expect(posted).toEqual([])
  })

  it("Entrée dans le champ valide le formulaire", async () => {
    const { user, posted } = setup(() => HttpResponse.json({ currency: "EUR", bank_balance: 10, numera_balance: 10, gap: 0, matches: true, verified: true, hints: [] }))

    await typeBalance(user, "10{Enter}")

    await waitFor(() => expect(posted).toHaveLength(1))
  })

  it("rapprochement refusé : message du serveur", async () => {
    const { user } = setup(() => HttpResponse.json({ detail: "Compte introuvable" }, { status: 404 }))

    await typeBalance(user, "10")
    await user.click(screen.getByRole("button", { name: "Vérifier" }))

    expect(await screen.findByText("Compte introuvable")).toBeInTheDocument()
  })

  it("« Fermer » ferme la fenêtre", async () => {
    const { user, onOpenChange } = setup(() => HttpResponse.json({}))

    await user.click(within(screen.getByRole("dialog")).getAllByRole("button", { name: "Fermer" })[0])

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
