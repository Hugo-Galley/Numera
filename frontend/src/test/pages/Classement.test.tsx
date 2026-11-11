/** Page Classement : quatre onglets (catégories, tags, marchands, règles), l'onglet de l'adresse est ouvert et l'adresse suit le choix. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { LocationDisplay } from "@/test/support/LocationDisplay"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import Classement from "@/pages/Classement"

beforeEach(() => {
  const empty = (path: string) => http.get(apiUrl(path), () => HttpResponse.json([]))
  server.use(
    empty("/categories"), empty("/tags"), empty("/merchants"), empty("/categorization-rules/"), empty("/transfer-rules"), empty("/accounts"),
    empty("/analytics/tags"), empty("/merchants/suggestions/unnormalized"),
    http.get(apiUrl("/analytics/expenses-by-category"), () => HttpResponse.json([])),
  )
})

const view = (route: string) => renderWithProviders(<><Classement /><LocationDisplay /></>, { route, auth: true })
const tab = (name: string) => screen.getByRole("tab", { name })

describe("page Classement", () => {
  it("par défaut, ouvre l'onglet Catégories parmi les quatre onglets", async () => {
    view("/classement")

    expect(screen.getByRole("heading", { name: "Classement" })).toBeInTheDocument()
    for (const name of ["Catégories", "Tags", "Marchands", "Règles"]) expect(tab(name)).toBeInTheDocument()
    expect(tab("Catégories")).toHaveAttribute("data-state", "active")
  })

  it("?tab= ouvre l'onglet demandé ; une valeur inconnue retombe sur Catégories", async () => {
    const first = view("/classement?tab=rules")
    expect(tab("Règles")).toHaveAttribute("data-state", "active")
    first.unmount()

    view("/classement?tab=nimportequoi")
    expect(tab("Catégories")).toHaveAttribute("data-state", "active")
  })

  it("choisir un onglet l'active et le reporte dans l'adresse", async () => {
    const { user } = view("/classement")

    await user.click(tab("Tags"))

    expect(tab("Tags")).toHaveAttribute("data-state", "active")
    expect(await screen.findByLabelText("adresse")).toHaveTextContent("/classement?tab=tags")
  })

  it("l'onglet Règles regroupe les règles de catégorisation et celles de virement", async () => {
    view("/classement?tab=rules")

    expect(await screen.findByText(/Aucune règle définie/)).toBeInTheDocument()
  })
})
