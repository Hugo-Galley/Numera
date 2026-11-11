/** Page introuvable : message et lien de retour au tableau de bord. */
import { screen } from "@testing-library/react"
import { renderWithProviders } from "@/test/support/render"
import NotFound from "@/pages/NotFound"

describe("NotFound", () => {
  it("annonce que la page n'existe pas et renvoie au tableau de bord", () => {
    renderWithProviders(<NotFound />, { route: "/inconnue" })

    expect(screen.getByRole("heading", { name: "Page introuvable" })).toBeInTheDocument()
    expect(screen.getByText("Cette adresse n'existe pas ou a été déplacée.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Retour au tableau de bord" })).toHaveAttribute("href", "/")
  })
})
