import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeActionCenter } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { useUI } from "@/providers/UIProvider"
import { Sidebar } from "@/components/layout/Sidebar"

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

  it("la page courante est mise en évidence, y compris « Paramètres » dans le menu mobile", async () => {
    renderWithProviders(<Sidebar hideBrand />, { auth: true, route: "/month/bilan" })

    expect(await screen.findByRole("link", { name: "Mois" })).toHaveAttribute("aria-current", "page")
    expect(screen.getByRole("link", { name: "Tableau de bord" })).not.toHaveAttribute("aria-current")
    expect(screen.getByRole("link", { name: "Paramètres" })).not.toHaveAttribute("aria-current")
  })

  it("« Paramètres » actif sur /settings dans le menu mobile", async () => {
    renderWithProviders(<Sidebar hideBrand />, { auth: true, route: "/settings" })

    expect(await screen.findByRole("link", { name: "Paramètres" })).toHaveAttribute("aria-current", "page")
  })

  it("menu mobile : pas de doublon confidentialité / recherche (déjà dans l'en-tête), Se déconnecter reste listé", async () => {
    renderWithProviders(<Sidebar hideBrand />, { auth: true })

    await screen.findByRole("link", { name: "Paramètres" })
    expect(screen.queryByRole("button", { name: "Rechercher" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Se déconnecter" })).toBeInTheDocument()
  })

  it("liste plus haute que l'écran : un indice « il y a la suite » apparaît et disparaît en bas", async () => {
    const height = vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(900)
    const client = vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(400)
    try {
      renderWithProviders(<Sidebar />, { auth: true })
      const hint = await screen.findByRole("button", { name: /d'autres entrées sont en dessous/ })
      expect(hint).toBeInTheDocument()

      // Défilé jusqu'en bas : l'indice s'efface
      const list = screen.getByRole("navigation").parentElement as HTMLElement
      list.scrollTop = 500
      list.dispatchEvent(new Event("scroll"))
      await waitFor(() => expect(screen.queryByRole("button", { name: /d'autres entrées sont en dessous/ })).not.toBeInTheDocument())
    } finally {
      height.mockRestore()
      client.mockRestore()
    }
  })

  it("liste entièrement visible : pas d'indice de défilement", async () => {
    renderWithProviders(<Sidebar />, { auth: true })

    await screen.findByRole("link", { name: "Centre d'actions" })
    expect(screen.queryByRole("button", { name: /d'autres entrées sont en dessous/ })).not.toBeInTheDocument()
  })

  it("l'entrée « Simulateur » mène à /tools", () => {
    renderWithProviders(<Sidebar />, { auth: true })

    expect(screen.getByRole("link", { name: "Simulateur" })).toHaveAttribute("href", "/tools")
  })
})
