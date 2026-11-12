/** Panneau « derrière ce chiffre » : le total et le nombre d'opérations viennent du backend (`GET /transactions/total`). */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { DrilldownSheet } from "@/components/transactions/DrilldownSheet"

const route = "/?dd_label=Courses&dd_m=3&dd_y=2026&dd_cat=7"

const row = (id: number, amount: number) => ({
  id, account_id: 1, date: "2026-03-05T00:00:00", merchant: `Marchand ${id}`, amount, reimbursement_offset: 0,
  note: null, category: { id: 7, name: "Courses" }, splits: [] as { category_id: number; amount: number }[],
})

function setup(rows: ReturnType<typeof row>[], total: { count: number; total: number }) {
  const seen: { list?: URLSearchParams; total?: URLSearchParams } = {}
  server.use(
    http.get(apiUrl("/transactions/total"), ({ request }) => {
      seen.total = new URL(request.url).searchParams
      return HttpResponse.json(total)
    }),
    http.get(apiUrl("/transactions"), ({ request }) => {
      seen.list = new URL(request.url).searchParams
      return HttpResponse.json(rows)
    }),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([{ id: 1, name: "Courant", currency: "EUR" }])),
  )
  renderWithProviders(<DrilldownSheet />, { auth: true, route })
  return seen
}

describe("DrilldownSheet", () => {
  it("affiche le nombre et le total calculés par le backend, pas la somme des lignes", async () => {
    setup([row(1, 10), row(2, 20)], { count: 1234, total: 4321.5 })

    expect(await screen.findByText(/1234 opérations/)).toBeInTheDocument()
    expect(screen.getByText(/4[\s  ]?321,50/)).toBeInTheDocument()
  })

  it("interroge le total avec les mêmes filtres que la liste, sans limite de page", async () => {
    const seen = setup([row(1, 10)], { count: 1, total: 10 })

    await screen.findByText(/1 opérations/)
    expect(seen.total?.get("category_id")).toBe("7")
    expect(seen.total?.get("type")).toBe("Sortie")
    expect(seen.total?.get("budget_scope")).toBe("true")
    expect(seen.total?.has("limit")).toBe(false)
    expect(seen.list?.get("limit")).toBe("500")
  })

  it("affiche sur chaque ligne la part de la catégorie filtrée pour une dépense découpée, nette des remboursements", async () => {
    const split = {
      ...row(1, 100), reimbursement_offset: 20,
      splits: [{ category_id: 7, amount: 60 }, { category_id: 8, amount: 40 }],
    }
    setup([split], { count: 1, total: 48 })

    expect(await screen.findByText("Marchand 1")).toBeInTheDocument()
    expect(screen.getAllByText(/48,00/).length).toBeGreaterThan(0)
  })

  it("propose de réessayer quand le chargement échoue, puis affiche le résultat", async () => {
    let fail = true
    server.use(
      http.get(apiUrl("/transactions/total"), () => HttpResponse.json({ count: 1, total: 10 })),
      http.get(apiUrl("/transactions"), () => (fail ? HttpResponse.error() : HttpResponse.json([row(1, 10)]))),
      http.get(apiUrl("/accounts"), () => HttpResponse.json([{ id: 1, name: "Courant", currency: "EUR" }])),
    )
    const { user } = renderWithProviders(<DrilldownSheet />, { auth: true, route })

    const retry = await screen.findByRole("button", { name: /réessayer|retry/i })
    fail = false
    await user.click(retry)

    expect(await screen.findByText("Marchand 1")).toBeInTheDocument()
  })
})
