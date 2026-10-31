/** Revue du mois : chargement, échec visible, clôture (marque sans verrouiller), dépense exceptionnelle, changement de mois. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { apiUrl } from "@/test/handlers"
import { LocationDisplay } from "@/test/LocationDisplay"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import type { MonthReview as MonthReviewData, ReviewTransaction } from "@/types/monthReview"
import MonthReview from "./MonthReview"

function makeExpense(overrides: Partial<ReviewTransaction> = {}): ReviewTransaction {
  return { id: 11, date: "2026-06-12T10:00:00", merchant: "Canapé", amount: 900, category_name: "Maison", is_exceptional: false, ...overrides }
}

function makeReview(overrides: Partial<MonthReviewData> = {}): MonthReviewData {
  return {
    year: 2026,
    month: 6,
    closed: false,
    closure: null,
    modified_since_close: false,
    categorize: { count: 0, total: 0, items: [] },
    accounts: { unverified_count: 0, accounts: [] },
    budget: {
      income: 3000,
      real_expenses: 2100,
      savings: 900,
      savings_rate: 30,
      burn_rate: 70,
      exceptional_expenses: 0,
      real_expenses_excl_exceptional: 2100,
      savings_excl_exceptional: 900,
      savings_rate_excl_exceptional: 30,
      burn_rate_excl_exceptional: 70,
      previous_real_expenses: 2000,
      alerts: [],
      top_expenses: [makeExpense()],
    },
    ...overrides,
  }
}

/** Mois budgétaire en cours : juillet 2026 (dernier mois terminé : juin). */
function serveReview(review: MonthReviewData | ((month: number) => MonthReviewData) = makeReview()) {
  server.use(
    http.get(apiUrl("/analytics/budget-period"), () => HttpResponse.json({ current: { year: 2026, month: 7 } })),
    http.get(apiUrl("/categories"), () => HttpResponse.json([])),
    http.get(apiUrl("/month-review"), ({ request }) => {
      const month = Number(new URL(request.url).searchParams.get("month"))
      return HttpResponse.json(typeof review === "function" ? review(month) : review)
    }),
  )
}

function renderReview(route = "/month/revue?year=2026&month=6") {
  return renderWithProviders(
    <Routes>
      <Route path="/month/revue" element={<><MonthReview /><LocationDisplay /></>} />
    </Routes>,
    { route, auth: true },
  )
}

const stepButton = (name: RegExp) => screen.getByRole("button", { name })

describe("MonthReview : chargement", () => {
  it("squelette puis première étape du mois demandé", async () => {
    serveReview(makeReview({ categorize: { count: 0, total: 0, items: [] } }))
    renderReview()

    expect(screen.getByText("juin 2026")).toBeInTheDocument()
    expect(screen.queryByText("Dépenses sans catégorie")).not.toBeInTheDocument()
    expect(await screen.findByText("Toutes les dépenses du mois sont catégorisées.")).toBeInTheDocument()
  })

  it("échec : ErrorState (pas un mois vide) et « Réessayer » recharge", async () => {
    let attempts = 0
    serveReview()
    server.use(
      http.get(apiUrl("/month-review"), () => {
        attempts++
        return attempts === 1 ? HttpResponse.json({ detail: "boom" }, { status: 500 }) : HttpResponse.json(makeReview())
      }),
    )
    const { user } = renderReview()

    expect(await screen.findByText("La revue du mois n'a pas pu être chargée.")).toBeInTheDocument()
    expect(screen.getByText("Impossible de charger la revue du mois")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Réessayer" }))

    await waitFor(() => expect(screen.queryByText("La revue du mois n'a pas pu être chargée.")).not.toBeInTheDocument())
    expect(attempts).toBe(2)
  })

  it("mois suivant bloqué au mois en cours ; mois précédent écrit l'adresse", async () => {
    serveReview((month) => makeReview({ month }))
    const { user } = renderReview("/month/revue?year=2026&month=7")

    await waitFor(() => expect(screen.getByRole("button", { name: "Mois suivant" })).toBeDisabled())
    await user.click(screen.getByRole("button", { name: "Mois précédent" }))

    expect(screen.getByRole("status", { name: "adresse" })).toHaveTextContent("/month/revue?year=2026&month=6")
    expect(screen.getByText("juin 2026")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Mois suivant" })).toBeEnabled()
  })

  it("changement de mois pendant un chargement lent : la réponse de l'ancien mois est ignorée", async () => {
    let releaseJune = () => {}
    const junePending = new Promise<void>((resolve) => (releaseJune = resolve))
    serveReview()
    server.use(
      http.get(apiUrl("/month-review"), async ({ request }) => {
        const month = Number(new URL(request.url).searchParams.get("month"))
        if (month === 6) {
          await junePending
          return HttpResponse.json(makeReview({ month: 6, categorize: { count: 3, total: 120, items: [] } }))
        }
        return HttpResponse.json(makeReview({ month, categorize: { count: 0, total: 0, items: [] } }))
      }),
    )
    const { user } = renderReview()

    await user.click(screen.getByRole("button", { name: "Mois précédent" }))
    expect(await screen.findByText("Toutes les dépenses du mois sont catégorisées.")).toBeInTheDocument()
    expect(screen.getByText("mai 2026")).toBeInTheDocument()

    releaseJune()
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(screen.getByText("Toutes les dépenses du mois sont catégorisées.")).toBeInTheDocument()
  })
})

describe("MonthReview : clôture", () => {
  it("clôturer envoie { year, month, highlight } et marque le mois sans verrouiller la page", async () => {
    const bodies: unknown[] = []
    serveReview()
    server.use(
      http.post(apiUrl("/month-review/close"), async ({ request }) => {
        bodies.push(await request.json())
        return HttpResponse.json(
          makeReview({
            closed: true,
            closure: { year: 2026, month: 6, closed_at: "2026-07-02T09:00:00", highlight: "Canapé", tx_count: 40, income: 3000, expenses: 2100, unresolved_count: 0 },
          }),
        )
      }),
    )
    const { user } = renderReview()
    await screen.findByText("Toutes les dépenses du mois sont catégorisées.")

    await user.click(await screen.findByRole("button", { name: /4\. Fait marquant/ }))
    await user.type(screen.getByLabelText(/Un fait marquant/), "  Canapé  ")
    await user.click(stepButton(/5\. Clôturer/))
    await user.click(screen.getByRole("button", { name: "Clôturer le mois" }))

    expect(await screen.findByText("Mois clôturé")).toBeInTheDocument()
    expect(bodies).toEqual([{ year: 2026, month: 6, highlight: "Canapé" }])
    expect(screen.getByText("Clôturé le 02/07/2026")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Re-clôturer le mois" })).toBeEnabled()
    expect(screen.getByRole("button", { name: "Rouvrir le mois" })).toBeEnabled()

    // Pas de verrouillage : les autres étapes restent modifiables
    await user.click(stepButton(/4\. Fait marquant/))
    expect(screen.getByLabelText(/Un fait marquant/)).toBeEnabled()
    await user.click(stepButton(/3\. Budget/))
    expect(screen.getByRole("button", { name: "Marquer exceptionnelle" })).toBeEnabled()
  })

  it("fait marquant vide : highlight null ; échec de clôture : toast, mois non marqué", async () => {
    const bodies: unknown[] = []
    serveReview()
    server.use(
      http.post(apiUrl("/month-review/close"), async ({ request }) => {
        bodies.push(await request.json())
        return HttpResponse.json({ detail: "boom" }, { status: 500 })
      }),
    )
    const { user } = renderReview()

    await user.click(await screen.findByRole("button", { name: /5\. Clôturer/ }))
    await user.click(await screen.findByRole("button", { name: "Clôturer le mois" }))

    expect(await screen.findByText("Échec de la clôture")).toBeInTheDocument()
    expect(bodies).toEqual([{ year: 2026, month: 6, highlight: null }])
    expect(screen.getByRole("button", { name: "Clôturer le mois" })).toBeEnabled()
    expect(screen.queryByRole("button", { name: "Rouvrir le mois" })).not.toBeInTheDocument()
  })

  it("rouvrir : DELETE du mois puis rechargement", async () => {
    let closed = true
    const deletes: string[] = []
    serveReview()
    server.use(
      http.get(apiUrl("/month-review"), () =>
        HttpResponse.json(
          makeReview({
            closed,
            closure: closed ? { year: 2026, month: 6, closed_at: "2026-07-02T09:00:00", highlight: null, tx_count: 1, income: 0, expenses: 0, unresolved_count: 2 } : null,
            modified_since_close: closed,
          }),
        ),
      ),
      http.delete(apiUrl("/month-review"), ({ request }) => {
        deletes.push(new URL(request.url).search)
        closed = false
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const { user } = renderReview()

    await user.click(await screen.findByRole("button", { name: /5\. Clôturer/ }))
    expect(await screen.findByText("2 point(s) restaient à traiter à la clôture.")).toBeInTheDocument()
    expect(screen.getByText(/Des transactions ont changé depuis la clôture/)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Rouvrir le mois" }))

    expect(await screen.findByText("Mois rouvert")).toBeInTheDocument()
    expect(deletes).toEqual(["?year=2026&month=6"])
    expect(await screen.findByRole("button", { name: "Clôturer le mois" })).toBeInTheDocument()
  })
})

describe("MonthReview : dépense exceptionnelle", () => {
  it("marquer exceptionnelle : PATCH is_exceptional, toast et rechargement", async () => {
    let exceptional = false
    const patches: unknown[] = []
    serveReview()
    server.use(
      http.get(apiUrl("/month-review"), () =>
        HttpResponse.json(
          makeReview({
            budget: {
              ...makeReview().budget,
              exceptional_expenses: exceptional ? 900 : 0,
              real_expenses_excl_exceptional: exceptional ? 1200 : 2100,
              top_expenses: [makeExpense({ is_exceptional: exceptional })],
            },
          }),
        ),
      ),
      http.patch(apiUrl("/transactions/:id"), async ({ request, params }) => {
        patches.push({ id: params.id, body: await request.json() })
        exceptional = true
        return HttpResponse.json({})
      }),
    )
    const { user } = renderReview()

    await user.click(await screen.findByRole("button", { name: /3\. Budget/ }))
    const item = (await screen.findByText("Canapé")).closest("li")!
    await user.click(within(item).getByRole("button", { name: "Marquer exceptionnelle" }))

    expect(await screen.findByText("Marquée exceptionnelle")).toBeInTheDocument()
    expect(patches).toEqual([{ id: "11", body: { is_exceptional: true } }])
    expect(await within(item).findByRole("button", { name: "Exceptionnelle" })).toBeInTheDocument()
    expect(screen.getByText("Dépenses hors exceptionnelles")).toBeInTheDocument()
    expect(screen.getByText(/dont 900,00\s€ exceptionnelles/)).toBeInTheDocument()
  })
})
