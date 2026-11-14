/** Espace « Mois » : onglets Bilan / Revue / Comparaison en sous-routes, l'actif est mis en évidence. */
import { screen } from "@testing-library/react"
import { Route, Routes } from "react-router-dom"
import { renderWithProviders } from "@/test/support/render"
import { stubPage } from "@/test/support/LocationDisplay"
import MonthHub from "@/pages/MonthHub"

function renderHub(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/month" element={<MonthHub />}>
        <Route path="bilan" element={<h2>Page du bilan</h2>} />
        <Route path="revue" element={<h2>Page de la revue</h2>} />
        <Route path="comparaison" element={<h2>Page de comparaison</h2>} />
      </Route>
      <Route path="*" element={stubPage("ailleurs")()} />
    </Routes>,
    { route },
  )
}

describe("MonthHub", () => {
  it("propose les trois onglets et affiche la sous-page de l'adresse", async () => {
    renderHub("/month/revue")

    expect(await screen.findByText("Page de la revue")).toBeInTheDocument()
    for (const name of ["Bilan", "Revue", "Comparaison"]) expect(screen.getByRole("link", { name })).toBeInTheDocument()
  })

  it("seul l'onglet courant est mis en évidence", async () => {
    renderHub("/month/bilan")
    await screen.findByText("Page du bilan")

    expect(screen.getByRole("link", { name: "Bilan" })).toHaveClass("bg-white")
    expect(screen.getByRole("link", { name: "Revue" })).not.toHaveClass("bg-white")
  })

  it("changer d'onglet change de sous-page", async () => {
    const { user } = renderHub("/month/bilan")
    await screen.findByText("Page du bilan")

    await user.click(screen.getByRole("link", { name: "Comparaison" }))

    expect(await screen.findByText("Page de comparaison")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Comparaison" })).toHaveClass("bg-white")
  })
})
