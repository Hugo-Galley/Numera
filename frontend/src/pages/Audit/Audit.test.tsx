/** Centre d'Actions : « Actualiser » relance l'analyse sans resservir la lecture mise en cache. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { makeActionCenter } from "@/test/factories"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import ActionCenter from "./index"

describe("Centre d'Actions", () => {
  it("« Actualiser » refait la requête d'analyse malgré le cache", async () => {
    let analyses = 0
    server.use(
      http.get(apiUrl("/analytics/actions"), () => {
        analyses += 1
        return HttpResponse.json(makeActionCenter())
      }),
      http.get(apiUrl("/categories"), () => HttpResponse.json([])),
      http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
    )
    const { user } = renderWithProviders(<ActionCenter />, { route: "/audit", auth: true })
    await waitFor(() => expect(analyses).toBe(1))

    await user.click(await screen.findByRole("button", { name: "Actualiser" }))

    await waitFor(() => expect(analyses).toBe(2))
  })
})
