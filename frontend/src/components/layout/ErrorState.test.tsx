import { screen } from "@testing-library/react"
import { renderWithProviders } from "@/test/render"
import { ErrorState } from "./ErrorState"

describe("ErrorState", () => {
  it("affiche le message et rappelle le chargement au clic sur « Réessayer »", async () => {
    const onRetry = vi.fn()
    const { user } = renderWithProviders(<ErrorState message="Comptes indisponibles" onRetry={onRetry} />)

    expect(screen.getByRole("alert")).toHaveTextContent("Comptes indisponibles")
    await user.click(screen.getByRole("button", { name: "Réessayer" }))

    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it("sans message ni onRetry : message par défaut, pas de bouton", () => {
    renderWithProviders(<ErrorState />)

    expect(screen.getByRole("alert")).toHaveTextContent("Impossible de charger ces données.")
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
  })
})
