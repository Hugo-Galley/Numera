/** Rappel de clôture du mois précédent : bandeau discret dans la page (plus de fenêtre modale à la connexion). */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { safeStorage } from "@/lib/storage"
import { MonthReviewReminder } from "@/components/month-review/MonthReviewReminder"
import { apiUrl } from "@/test/support/handlers"
import { LocationDisplay } from "@/test/support/LocationDisplay"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

/** Mois budgétaire en cours : novembre 2026 → rappel pour octobre. */
function serve({ closures = [] as object[], income = 2500 } = {}) {
  server.use(
    http.get(apiUrl("/analytics/budget-period"), () => HttpResponse.json({ current: { year: 2026, month: 11 } })),
    http.get(apiUrl("/month-review/closures"), () => HttpResponse.json(closures)),
    http.get(apiUrl("/month-review"), () =>
      HttpResponse.json({
        year: 2026, month: 10,
        categorize: { count: 2 }, accounts: { unverified_count: 1 },
        budget: { income, real_expenses: income ? 1800 : 0 },
      }),
    ),
  )
}

const view = () => renderWithProviders(<><MonthReviewReminder /><LocationDisplay /></>, { auth: true })

describe("MonthReviewReminder", () => {
  it("mois précédent non clôturé : bandeau dans la page, sans fenêtre modale", async () => {
    serve()
    view()

    const banner = await screen.findByRole("region", { name: "Rappel de clôture du mois" })
    expect(banner).toHaveTextContent("Octobre n'est pas encore clôturé")
    expect(banner).toHaveTextContent(/2 dépense\(s\) sans catégorie et 1 compte\(s\) à valider/)
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("« Faire la revue » ouvre la revue du mois concerné", async () => {
    serve()
    const { user } = view()

    await user.click(await screen.findByRole("button", { name: "Faire la revue" }))
    expect(screen.getByLabelText("adresse")).toHaveTextContent("/month/revue?year=2026&month=10")
  })

  it("« Plus tard » masque le rappel pour la journée", async () => {
    serve()
    const { user } = view()

    await user.click(await screen.findByRole("button", { name: "Plus tard" }))
    expect(screen.queryByRole("region", { name: "Rappel de clôture du mois" })).not.toBeInTheDocument()
    expect(safeStorage.getItem("month-review-snooze-2026-10")).toBe(new Date().toLocaleDateString("sv-SE"))
  })

  it("la croix l'écarte pour ce mois", async () => {
    serve()
    const { user } = view()

    await user.click(await screen.findByRole("button", { name: "Ne plus me le rappeler pour ce mois" }))
    expect(screen.queryByRole("region", { name: "Rappel de clôture du mois" })).not.toBeInTheDocument()
    expect(safeStorage.getItem("month-review-skip-2026-10")).toBe("1")
  })

  it("mois déjà clôturé : aucun rappel", async () => {
    serve({ closures: [{ year: 2026, month: 10 }] })
    view()

    await waitFor(() => expect(screen.getByLabelText("adresse")).toBeInTheDocument())
    await new Promise((r) => setTimeout(r, 50))
    expect(screen.queryByRole("region", { name: "Rappel de clôture du mois" })).not.toBeInTheDocument()
  })
})
