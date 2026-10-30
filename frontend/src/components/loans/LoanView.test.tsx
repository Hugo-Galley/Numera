/** Vue d'un crédit : chargement, simulation et enregistrement d'un remboursement anticipé, suppression. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { apiUrl } from "@/test/handlers"
import { LocationDisplay } from "@/test/LocationDisplay"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { LoanView } from "./LoanView"
import type { LoanSummary } from "./types"

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

type Body = Record<string, unknown>

const schedule = [
  { n: 1, date: "2024-02-05", payment: 1012.5, interest: 600, principal: 412.5, insurance: 25.5, remaining: 199587.5, prepayment: 0 },
  { n: 2, date: "2024-03-05", payment: 1012.5, interest: 598.76, principal: 413.74, insurance: 25.5, remaining: 199173.76, prepayment: 0 },
]
const simulation = { interest_saved: 8420.12, total_interest_before: 103750, total_interest_after: 95329.88, new_end_date: "2046-07-05", months_saved: 30, new_payment: 960, max_penalty: 300 }

function setup(loan: LoanSummary = makeLoan()) {
  const posted: { path: string; body: Body }[] = []
  let loads = 0
  server.use(
    http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
    http.get(apiUrl("/loans/by-account/12"), () => {
      loads++
      return HttpResponse.json(loan)
    }),
    http.get(apiUrl("/loans/8/schedule"), () => HttpResponse.json(schedule)),
    http.post(apiUrl("/loans/8/:action"), async ({ request }) => {
      const body = (await request.json()) as Body
      const path = new URL(request.url).pathname
      posted.push({ path, body })
      return HttpResponse.json(path.endsWith("simulate-prepayment") ? simulation : {})
    }),
  )
  const view = renderWithProviders(
    <Routes>
      <Route path="/accounts/12" element={<LoanView accountId={12} />} />
      <Route path="*" element={<LocationDisplay />} />
    </Routes>,
    { route: "/accounts/12", auth: true },
  )
  return { ...view, posted, loads: () => loads }
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date("2026-06-15T10:00:00"))
})
afterEach(() => vi.useRealTimers())

describe("LoanView", () => {
  it("affiche une erreur avec « Réessayer » si le crédit ne charge pas", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined)
    setup()
    server.use(http.get(apiUrl("/loans/by-account/12"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))

    expect(await screen.findByText("Impossible de charger ce crédit.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument()
  })

  it("refuse de simuler sans montant", async () => {
    const { user, posted } = setup()

    await user.click(await screen.findByRole("button", { name: "Simuler" }))

    expect(await screen.findByText("Indiquez un montant à rembourser.")).toBeInTheDocument()
    expect(posted).toHaveLength(0)
  })

  it("simule (réduire la mensualité), puis enregistre le remboursement après confirmation", async () => {
    const { user, posted, loads } = setup()

    await user.type(await screen.findByLabelText("Montant (€)"), "10 000,50")
    await user.clear(screen.getByLabelText("Date"))
    await user.type(screen.getByLabelText("Date"), "2026-09-05")
    await user.click(screen.getByRole("combobox"))
    await user.click(await screen.findByRole("option", { name: "Réduire la mensualité" }))
    await user.click(screen.getByRole("button", { name: "Simuler" }))

    expect(await screen.findByText(/d'intérêts économisés/)).toBeInTheDocument()
    expect(screen.getByText(/Nouvelle mensualité/)).toBeInTheDocument()
    expect(posted).toEqual([{ path: expect.stringMatching(/\/loans\/8\/simulate-prepayment$/), body: { amount: 10000.5, date: "2026-09-05", mode: "reduce_payment" } }])

    await user.click(screen.getByRole("button", { name: "J'ai effectué ce remboursement" }))
    const confirmDialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(confirmDialog).toHaveTextContent("5 septembre 2026")
    // Bouton rouge « Supprimer » pour valider un enregistrement : voir le it.todo plus bas
    await user.click(within(confirmDialog).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Remboursement anticipé enregistré")).toBeInTheDocument()
    expect(posted[1]).toEqual({ path: expect.stringMatching(/\/loans\/8\/prepayments$/), body: { amount: 10000.5, date: "2026-09-05", mode: "reduce_payment" } })
    await waitFor(() => expect(loads()).toBe(2))
    expect(screen.getByLabelText("Montant (€)")).toHaveValue("")
    expect(screen.queryByText(/d'intérêts économisés/)).not.toBeInTheDocument()
  })

  it("n'enregistre rien si la confirmation est annulée", async () => {
    const { user, posted } = setup()

    await user.type(await screen.findByLabelText("Montant (€)"), "5000")
    await user.click(screen.getByRole("button", { name: "Simuler" }))
    await user.click(await screen.findByRole("button", { name: "J'ai effectué ce remboursement" }))
    await user.click(await screen.findByRole("button", { name: "Annuler" }))

    expect(posted.map((p) => p.path.split("/").pop())).toEqual(["simulate-prepayment"])
    expect(screen.getByText(/d'intérêts économisés/)).toBeInTheDocument()
  })

  it("une modification du montant efface la simulation affichée", async () => {
    const { user } = setup()

    const amount = await screen.findByLabelText("Montant (€)")
    await user.type(amount, "5000")
    await user.click(screen.getByRole("button", { name: "Simuler" }))
    await screen.findByText(/d'intérêts économisés/)
    await user.type(amount, "0")

    expect(screen.queryByText(/d'intérêts économisés/)).not.toBeInTheDocument()
  })

  it("supprime un remboursement anticipé après confirmation", async () => {
    const deleted: string[] = []
    const { user } = setup(makeLoan({ prepayments: [{ id: 41, date: "2025-03-05", amount: 5000, mode: "reduce_duration" }] }))
    server.use(
      http.delete(apiUrl("/loans/8/prepayments/41"), ({ request }) => {
        deleted.push(request.method)
        return HttpResponse.json({})
      }),
    )

    await user.click(await screen.findByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Remboursement anticipé supprimé")).toBeInTheDocument()
    expect(deleted).toEqual(["DELETE"])
  })

  it("supprime le crédit après confirmation et revient aux comptes", async () => {
    const { user } = setup()
    server.use(http.delete(apiUrl("/loans/8"), () => HttpResponse.json({})))

    await user.click(await screen.findByRole("button", { name: "Supprimer le crédit" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Crédit supprimé")).toBeInTheDocument()
    expect(screen.getByRole("status", { name: "adresse" })).toHaveTextContent("/accounts")
  })

  // Bug suspect (LoanView.tsx, handleRecord) : confirm("Enregistrer un remboursement anticipé…") est appelé sans
  // { destructive: false, confirmLabel } ; la boîte affiche donc un bouton rouge « Supprimer » pour valider un
  // enregistrement. Attendu : un bouton « Enregistrer » (ou « Confirmer ») non destructif.
  it.todo("confirme l'enregistrement d'un remboursement anticipé avec un bouton non destructif")
})
