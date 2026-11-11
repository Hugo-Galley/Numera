/** Page Outils : vue simple (prévision de patrimoine, projection FIRE) et mode avancé (simulateur) alimenté par le capital actuel. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import Tools from "@/pages/Tools"

/** Prévision et FIRE répondent en erreur : le test porte sur la page, leurs états d'erreur suffisent à les identifier. */
function serve(allocation: () => Response = () => HttpResponse.json({ total_current_value: 25000 })) {
  let allocations = 0
  server.use(
    http.get(apiUrl("/analytics/investments-allocation"), () => { allocations += 1; return allocation() }),
    http.get(apiUrl("/analytics/wealth-forecast"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
    http.get(apiUrl("/analytics/fire"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    http.get(apiUrl("/analytics/investments-allocation-advanced"), () => HttpResponse.json({})),
    http.get(apiUrl("/analytics/patrimoine-allocation"), () => HttpResponse.json({})),
  )
  return { allocations: () => allocations }
}

const view = () => renderWithProviders(<Tools />, { route: "/tools", auth: true })

describe("page Outils", () => {
  it("vue simple : titre, prévision de patrimoine et projection FIRE", async () => {
    serve()
    view()

    expect(screen.getByRole("heading", { name: "Outils" })).toBeInTheDocument()
    expect(screen.getByText("Simulez et projetez l'évolution de votre patrimoine.")).toBeInTheDocument()
    expect(await screen.findByText("Impossible de calculer la projection", { exact: false })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Mode avancé" })).toBeInTheDocument()
  })

  it("« Mode avancé » remplace la vue simple par le simulateur ; « Retour à la vue simple » revient", async () => {
    const { allocations } = serve()
    const { user } = view()
    await waitFor(() => expect(allocations()).toBe(1))

    await user.click(screen.getByRole("button", { name: "Mode avancé" }))
    expect(await screen.findByRole("button", { name: "Retour à la vue simple" })).toBeInTheDocument()
    expect(screen.queryByText("Impossible de calculer la projection", { exact: false })).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Retour à la vue simple" }))
    expect(await screen.findByRole("button", { name: "Mode avancé" })).toBeInTheDocument()
  })

  it("allocation indisponible : message d'erreur, la page reste utilisable", async () => {
    serve(() => HttpResponse.json({ detail: "KO" }, { status: 500 }))
    const { user } = view()

    expect(await screen.findByText("Impossible de charger l'allocation du patrimoine")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Mode avancé" }))
    expect(await screen.findByRole("button", { name: "Retour à la vue simple" })).toBeInTheDocument()
  })
})
