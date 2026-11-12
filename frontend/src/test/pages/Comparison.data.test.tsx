/** Comparaison de deux mois : écarts, lignes par catégorie, drill-down, erreur et rechargement. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { LocationDisplay } from "@/test/support/LocationDisplay"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import Comparison from "@/pages/Comparison"

const cat = (id: number, name: string, total: number, color = "#10b981") => ({ category: { id, name, color }, total })

/** Juin 2026 (A) contre mai 2026 (B). */
function serve({ failing = false } = {}) {
  const requests: string[] = []
  server.use(
    http.get(apiUrl("/analytics/budget"), ({ request }) => {
      const url = new URL(request.url)
      requests.push(`budget ${url.searchParams.get("month")}/${url.searchParams.get("year")}`)
      if (failing) return new HttpResponse(null, { status: 500 })
      return HttpResponse.json(url.searchParams.get("month") === "6"
        ? { revenus_totaux: 3000, depenses_reelles: 1500, epargne_realisee: 1500 }
        : { revenus_totaux: 2000, depenses_reelles: 1800, epargne_realisee: 200 })
    }),
    http.get(apiUrl("/analytics/expenses-by-category"), ({ request }) => {
      const june = new URL(request.url).searchParams.get("month") === "6"
      return HttpResponse.json({ items: june
        ? [cat(1, "Courses", 400), cat(2, "Loisirs", 100), cat(4, "Cadeaux", 50)]
        : [cat(1, "Courses", 500), cat(2, "Loisirs", 100), cat(3, "Voyage", 300)] })
    }),
  )
  return requests
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date(2026, 5, 15))
})
afterEach(() => vi.useRealTimers())

const renderPage = (route = "/") => renderWithProviders(<><Comparison /><LocationDisplay /></>, { auth: true, route })

describe("Comparison : chiffres", () => {
  it("charge A (juin) et B (mai), affiche les trois écarts", async () => {
    const requests = serve()
    renderPage()

    expect(await screen.findAllByText("Courses")).not.toHaveLength(0)
    expect(requests).toEqual(expect.arrayContaining(["budget 6/2026", "budget 5/2026"]))
    const card = (label: string) => screen.getByText(label).closest("div[class*='rounded']")!.parentElement!
    expect(card("Écart Revenus")).toHaveTextContent(/1\s000,00\s€/)
    expect(card("Écart Revenus")).toHaveTextContent(/50,0\s?%/)
    expect(card("Écart Dépenses")).toHaveTextContent(/300,00\s€/)
    expect(card("Écart Dépenses")).toHaveTextContent(/-16,7\s?%/)
    expect(card("Écart Épargne")).toHaveTextContent(/1\s300,00\s€/)
  })

  it("lignes par catégorie : triées par écart décroissant, « nouveau » sans montant en B, pourcentages signés", async () => {
    serve()
    renderPage()
    await screen.findAllByText("Courses")

    const table = screen.getByRole("table")
    const rows = within(table).getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell").map((c) => c.textContent))
    expect(rows.map((r) => r[0])).toEqual(["Cadeaux", "Loisirs", "Courses", "Voyage"])
    expect(rows[0][4]).toBe("nouveau")
    expect(rows[1][4]).toMatch(/^0,0\s?%$/) // écart nul, mais base en B
    expect(rows[2][4]).toMatch(/-20,0\s?%/)
    expect(rows[3][4]).toMatch(/-100,0\s?%/)
  })

  it("montant d'une catégorie : ouvre le détail de la bonne période ; désactivé à zéro", async () => {
    serve()
    const { user } = renderPage()
    await screen.findAllByText("Courses")

    const table = screen.getByRole("table")
    const courses = within(table).getByRole("row", { name: /Courses/ })
    const [valB, valA] = within(courses).getAllByRole("button")
    await user.click(valB)
    await waitFor(() => expect(screen.getByLabelText("adresse")).toHaveTextContent(/dd_m=5/))
    expect(screen.getByLabelText("adresse")).toHaveTextContent(/dd_y=2026/)
    expect(screen.getByLabelText("adresse")).toHaveTextContent(/dd_cat=1/)

    await user.click(valA)
    await waitFor(() => expect(screen.getByLabelText("adresse")).toHaveTextContent(/dd_m=6/))

    // Cadeaux n'a rien en B : bouton B désactivé
    const gifts = within(table).getByRole("row", { name: /Cadeaux/ })
    expect(within(gifts).getAllByRole("button")[0]).toBeDisabled()
  })

  it("changer la période A relance le chargement de cette période", async () => {
    const requests = serve()
    const { user } = renderPage()
    await screen.findAllByText("Courses")

    await user.click(screen.getAllByRole("combobox")[0])
    await user.click(await screen.findByRole("option", { name: /mars/i }))

    await waitFor(() => expect(requests).toContain("budget 3/2026"))
  })

  it("sans aucune dépense : message d'invite", async () => {
    server.use(
      http.get(apiUrl("/analytics/budget"), () => HttpResponse.json({})),
      http.get(apiUrl("/analytics/expenses-by-category"), () => HttpResponse.json({ items: [] })),
    )
    renderPage()

    expect((await screen.findAllByText(/Sélectionnez deux périodes/i)).length).toBeGreaterThan(0)
  })

  it("revenus nuls en B : pas de pourcentage d'écart (tiret)", async () => {
    server.use(
      http.get(apiUrl("/analytics/budget"), ({ request }) =>
        HttpResponse.json(new URL(request.url).searchParams.get("month") === "6" ? { revenus_totaux: 500 } : {})),
      http.get(apiUrl("/analytics/expenses-by-category"), () => HttpResponse.json({ items: [] })),
    )
    renderPage()

    const label = await screen.findByText("Écart Revenus")
    await waitFor(() => expect(label.closest("div[class*='rounded']")!.parentElement).toHaveTextContent("—"))
  })

  it("échec : erreur affichée, « Réessayer » recharge", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {})
    let failing = true
    server.use(
      http.get(apiUrl("/analytics/budget"), () => (failing ? new HttpResponse(null, { status: 500 }) : HttpResponse.json({ revenus_totaux: 1 }))),
      http.get(apiUrl("/analytics/expenses-by-category"), () => HttpResponse.json({ items: [cat(1, "Courses", 10)] })),
    )
    const { user } = renderPage()

    const retry = await screen.findByRole("button", { name: /Réessayer/ })
    failing = false
    await user.click(retry)

    expect(await screen.findAllByText("Courses")).not.toHaveLength(0)
    expect(screen.queryByRole("button", { name: /Réessayer/ })).not.toBeInTheDocument()
  })
})
