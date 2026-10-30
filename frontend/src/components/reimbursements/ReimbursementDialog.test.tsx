/** Créances sur une dépense (« On me doit ») : validation, ajout, répartition, erreurs serveur. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { ReimbursementDialog } from "./ReimbursementDialog"

type Body = Record<string, unknown>

const expense = { id: 30, type: "Sortie", merchant: "Restaurant", date: "2026-06-10T20:00:00", amount: 100, currency: "EUR" }

function setup(onPost: () => Response | Promise<Response> = () => HttpResponse.json({ id: 1 })) {
  const posted: Body[] = []
  server.use(
    http.get(apiUrl("/reimbursements/claims"), () => HttpResponse.json([])),
    http.post(apiUrl("/reimbursements/claims"), async ({ request }) => {
      posted.push((await request.json()) as Body)
      return onPost()
    }),
  )
  const onDone = vi.fn()
  const view = renderWithProviders(<ReimbursementDialog open transaction={expense} onOpenChange={vi.fn()} onDone={onDone} />, { auth: true })
  return { ...view, posted, onDone }
}

describe("ReimbursementDialog : dépense", () => {
  it("exige un débiteur et un montant positif", async () => {
    const { user, posted } = setup()
    await screen.findByText("Aucune créance sur cette dépense.")

    await user.type(screen.getByLabelText("Qui me doit"), "Denis")
    await user.type(screen.getByLabelText("Montant"), "-20")
    await user.click(screen.getByRole("button", { name: "Ajouter" }))

    expect(await screen.findByText("Indiquez un débiteur et un montant")).toBeInTheDocument()
    expect(posted).toHaveLength(0)
  })

  it("ajoute une créance (virgule décimale) et prévient le parent", async () => {
    const { user, posted, onDone } = setup()
    await screen.findByText("Aucune créance sur cette dépense.")

    await user.type(screen.getByLabelText("Qui me doit"), " Denis ")
    await user.type(screen.getByLabelText("Montant"), "33,50")
    await user.click(screen.getByRole("button", { name: "Ajouter" }))

    expect(await screen.findByText("Créance ajoutée")).toBeInTheDocument()
    expect(posted).toEqual([{ transaction_id: 30, debtor: "Denis", expected_amount: 33.5 }])
    expect(onDone).toHaveBeenCalled()
    expect(screen.getByLabelText("Qui me doit")).toHaveValue("")
  })

  it("répartit à parts égales : n − 1 créances arrondies au centime inférieur", async () => {
    const { user, posted } = setup()
    await screen.findByText("Aucune créance sur cette dépense.")

    await user.clear(screen.getByLabelText("Partager à parts égales entre (vous compris)"))
    await user.type(screen.getByLabelText("Partager à parts égales entre (vous compris)"), "3")
    await user.click(screen.getByRole("button", { name: "Répartir" }))

    expect(await screen.findByText(/2 créances de 33,33\s€ ajoutées/)).toBeInTheDocument()
    expect(posted).toEqual([
      { transaction_id: 30, debtor: "Personne 1", expected_amount: 33.33 },
      { transaction_id: 30, debtor: "Personne 2", expected_amount: 33.33 },
    ])
  })

  it("affiche le détail de l'erreur serveur", async () => {
    const { user, onDone } = setup(() => HttpResponse.json({ detail: "Créance supérieure à la dépense" }, { status: 400 }))
    await screen.findByText("Aucune créance sur cette dépense.")

    await user.type(screen.getByLabelText("Qui me doit"), "Denis")
    await user.type(screen.getByLabelText("Montant"), "500")
    await user.click(screen.getByRole("button", { name: "Ajouter" }))

    expect(await screen.findByText("Créance supérieure à la dépense")).toBeInTheDocument()
    await waitFor(() => expect(onDone).not.toHaveBeenCalled())
  })

  // Bug suspect (ReimbursementDialog.tsx, handleAdd / handleSplit) : pas de useSubmit ni de bouton désactivé ;
  // deux clics sur « Ajouter » pendant que le POST /reimbursements/claims est en cours créent deux créances.
  // Attendu : bouton désactivé pendant l'envoi, une seule requête.
  it.todo("désactive « Ajouter » et « Répartir » pendant l'envoi")
})
