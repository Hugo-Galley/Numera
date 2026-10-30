import { screen } from "@testing-library/react"
import { renderWithProviders } from "@/test/render"
import { ErrorBoundary } from "./ErrorBoundary"

let shouldThrow = true

function Fragile() {
  if (shouldThrow) throw new Error("boum")
  return <p>Contenu rétabli</p>
}

beforeEach(() => {
  shouldThrow = true
  // React et componentDidCatch journalisent l'erreur : attendu ici, on garde la sortie propre
  vi.spyOn(console, "error").mockImplementation(() => {})
})

describe("ErrorBoundary", () => {
  it("laisse passer un enfant qui se rend normalement", () => {
    shouldThrow = false
    renderWithProviders(<ErrorBoundary><Fragile /></ErrorBoundary>)

    expect(screen.getByText("Contenu rétabli")).toBeInTheDocument()
  })

  it("un enfant qui jette affiche l'écran d'erreur, pas une page blanche", () => {
    renderWithProviders(
      <div>
        <h1>Menu</h1>
        <ErrorBoundary><Fragile /></ErrorBoundary>
      </div>,
    )

    expect(screen.getByRole("heading", { name: "Cette page a rencontré une erreur" })).toBeInTheDocument()
    expect(screen.getByText(/Vos données ne sont pas affectées/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Recharger" })).toBeInTheDocument()
    // Le reste de l'app (menu) reste affiché
    expect(screen.getByRole("heading", { name: "Menu" })).toBeInTheDocument()
    expect(console.error).toHaveBeenCalledWith("Erreur de rendu :", expect.objectContaining({ message: "boum" }), expect.any(String))
  })

  it("« Réessayer » rend à nouveau les enfants", async () => {
    const { user } = renderWithProviders(<ErrorBoundary><Fragile /></ErrorBoundary>)
    expect(screen.getByRole("heading", { name: "Cette page a rencontré une erreur" })).toBeInTheDocument()

    shouldThrow = false
    await user.click(screen.getByRole("button", { name: "Réessayer" }))

    expect(screen.getByText("Contenu rétabli")).toBeInTheDocument()
    expect(screen.queryByText("Cette page a rencontré une erreur")).not.toBeInTheDocument()
  })

  it("« Recharger » recharge la page", async () => {
    const reload = vi.fn()
    vi.spyOn(window, "location", "get").mockReturnValue({ ...window.location, reload })
    const { user } = renderWithProviders(<ErrorBoundary fullPage><Fragile /></ErrorBoundary>)

    await user.click(screen.getByRole("button", { name: "Recharger" }))

    expect(reload).toHaveBeenCalledTimes(1)
  })
})
