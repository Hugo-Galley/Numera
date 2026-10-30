import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeActionCenter } from "@/test/factories"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { useUI } from "@/providers/UIProvider"
import { Sidebar } from "./Sidebar"

function SearchState() {
  const { isSearchOpen } = useUI()
  return <p>recherche : {isSearchOpen ? "ouverte" : "fermée"}</p>
}

const urgent = (high_priority: number) =>
  server.use(
    http.get(apiUrl("/analytics/actions"), () =>
      HttpResponse.json(makeActionCenter({ summary: { ...makeActionCenter().summary, high_priority } })),
    ),
  )

describe("Sidebar", () => {
  it("affiche la pastille d'actions urgentes sur « Centre d'actions »", async () => {
    urgent(3)
    renderWithProviders(<Sidebar />, { auth: true })

    const link = screen.getByRole("link", { name: /Centre d'actions/ })
    expect(await within(link).findByLabelText("3 actions urgentes")).toHaveTextContent("3")
  })

  it("sans action urgente, pas de pastille", async () => {
    renderWithProviders(<Sidebar />, { auth: true })

    await screen.findByRole("link", { name: "Centre d'actions" })
    expect(screen.queryByLabelText(/actions urgentes/)).not.toBeInTheDocument()
  })

  it("le bouton « Rechercher » ouvre l'omnibox", async () => {
    const { user } = renderWithProviders(<><Sidebar /><SearchState /></>, { auth: true })

    await user.click(screen.getByRole("button", { name: "Rechercher" }))

    expect(screen.getByText("recherche : ouverte")).toBeInTheDocument()
  })

  it("le menu mobile liste « Paramètres » et « Se déconnecter » à plat", async () => {
    renderWithProviders(<Sidebar hideBrand />, { auth: true })

    expect(screen.getByRole("link", { name: "Paramètres" })).toHaveAttribute("href", "/settings")
    expect(screen.getByRole("button", { name: "Se déconnecter" })).toBeInTheDocument()
    expect(await screen.findByText("admin")).toBeInTheDocument()
  })
})
