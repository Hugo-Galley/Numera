/** Saisie d'un crédit : validation, conversion des champs (virgule, années → mois), création, modification, erreurs. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { LoanDialog } from "./LoanDialog"
import type { LoanSummary } from "./types"

type Body = Record<string, unknown>

const makeLoan = (overrides: Partial<LoanSummary> = {}): LoanSummary => ({
  id: 8,
  account_id: 12,
  name: "Prêt appartement",
  institution: "BRED",
  logo: null,
  color: null,
  kind: "immobilier",
  principal: 200000,
  annual_rate_pct: 3.6,
  duration_months: 300,
  start_date: "2024-02-05",
  insurance_monthly: 25.5,
  monthly_payment: 1012.5,
  remaining_principal: 190000,
  repaid_pct: 5,
  end_date: "2049-01-05",
  total_interest: 103750,
  total_insurance: 7650,
  total_cost: 111400,
  prepayments: [],
  ...overrides,
})

function setup(loan: LoanSummary | null = null, respond: (body: Body) => Response | Promise<Response> = (body) => HttpResponse.json({ ...makeLoan(), ...body })) {
  const sent: { method: string; path: string; body: Body }[] = []
  const handle = async ({ request }: { request: Request }) => {
    const body = (await request.json()) as Body
    sent.push({ method: request.method, path: new URL(request.url).pathname, body })
    return respond(body)
  }
  server.use(http.post(apiUrl("/loans"), handle), http.patch(apiUrl("/loans/:id"), handle))
  const onSaved = vi.fn()
  const onOpenChange = vi.fn()
  const view = renderWithProviders(<LoanDialog open loan={loan} onSaved={onSaved} onOpenChange={onOpenChange} />, { auth: true })
  return { ...view, sent, onSaved, onOpenChange, dialog: screen.getByRole("dialog") }
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date("2026-06-15T10:00:00"))
})
afterEach(() => vi.useRealTimers())

describe("LoanDialog", () => {
  it("refuse une durée de moins d'un mois sans rien envoyer", async () => {
    const { user, sent, dialog } = setup()

    await user.type(within(dialog).getByLabelText("Nom"), "Prêt auto")
    await user.type(within(dialog).getByLabelText("Montant emprunté (€)"), "15000")
    await user.type(within(dialog).getByLabelText("Durée (années)"), "0,02")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Renseignez le nom, le montant, le taux, la durée et la date de première échéance.")).toBeInTheDocument()
    expect(sent).toHaveLength(0)
  })

  it("crée le crédit : virgules et espaces, années converties en mois, taux vide = 0, date du jour par défaut", async () => {
    const { user, sent, onSaved, onOpenChange, dialog } = setup()

    expect(within(dialog).getByLabelText("Première échéance")).toHaveValue("2026-06-15")
    await user.type(within(dialog).getByLabelText("Nom"), "  Prêt auto ")
    await user.type(within(dialog).getByLabelText("Banque"), "Crédit Mutuel")
    await user.type(within(dialog).getByLabelText("Montant emprunté (€)"), "15 000,50")
    await user.type(within(dialog).getByLabelText("Durée (années)"), "4,5")
    await user.type(within(dialog).getByLabelText("Assurance emprunteur (€ / mois)"), "9,90")
    await user.click(within(dialog).getAllByRole("combobox")[0])
    await user.click(await screen.findByRole("option", { name: "Auto" }))
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Crédit ajouté")).toBeInTheDocument()
    expect(sent).toEqual([
      {
        method: "POST",
        path: "/loans",
        body: {
          name: "Prêt auto",
          institution: "Crédit Mutuel",
          logo: null,
          kind: "auto",
          principal: 15000.5,
          annual_rate_pct: 0,
          duration_months: 54,
          start_date: "2026-06-15",
          insurance_monthly: 9.9,
        },
      },
    ])
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ name: "Prêt auto" }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it("préremplit un crédit existant et l'enregistre par PATCH", async () => {
    const { user, sent, dialog } = setup(makeLoan())

    expect(within(dialog).getByLabelText("Montant emprunté (€)")).toHaveValue("200000")
    expect(within(dialog).getByLabelText("Taux nominal annuel (%)")).toHaveValue("3,6")
    expect(within(dialog).getByLabelText("Durée (années)")).toHaveValue("25")
    expect(within(dialog).getByLabelText("Assurance emprunteur (€ / mois)")).toHaveValue("25,5")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Crédit mis à jour")).toBeInTheDocument()
    expect(sent[0]).toMatchObject({
      method: "PATCH",
      path: "/loans/8",
      body: { principal: 200000, annual_rate_pct: 3.6, duration_months: 300, start_date: "2024-02-05", insurance_monthly: 25.5 },
    })
  })

  it("affiche « Enregistrement… » désactivé pendant l'envoi", async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    const { user, sent, dialog } = setup(makeLoan(), async (body) => {
      await gate
      return HttpResponse.json({ ...makeLoan(), ...body })
    })

    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))
    const busy = await within(dialog).findByRole("button", { name: "Enregistrement…" })
    expect(busy).toBeDisabled()
    await user.click(busy)
    release()
    await screen.findByText("Crédit mis à jour")
    expect(sent).toHaveLength(1)
  })

  it("affiche le détail de l'erreur serveur sans fermer", async () => {
    const { user, onOpenChange, onSaved, dialog } = setup(makeLoan(), () =>
      HttpResponse.json({ detail: "Taux hors limites" }, { status: 422 }),
    )

    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Taux hors limites")).toBeInTheDocument()
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "Enregistrer" })).toBeEnabled())
    expect(onSaved).not.toHaveBeenCalled()
    expect(onOpenChange).not.toHaveBeenCalled()
  })
})
