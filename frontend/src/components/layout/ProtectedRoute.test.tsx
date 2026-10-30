import { screen } from "@testing-library/react"
import { Route, Routes, useLocation } from "react-router-dom"
import { renderWithProviders } from "@/test/render"
import { safeStorage } from "@/lib/storage"
import { ProtectedRoute } from "./ProtectedRoute"

/** Page de connexion factice : montre d'où vient la redirection (`state.from`). */
function LoginStub() {
  const { state } = useLocation()
  const from = (state as { from?: { pathname: string; search: string } } | null)?.from
  return <h1>Connexion depuis {from ? from.pathname + from.search : "nulle part"}</h1>
}

function renderAt(route: string, auth: boolean | { expInMinutes: number }) {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<LoginStub />} />
      <Route path="/accounts" element={<ProtectedRoute><h1>Mes comptes</h1></ProtectedRoute>} />
    </Routes>,
    { route, auth },
  )
}

describe("ProtectedRoute", () => {
  it("sans jeton, redirige vers /login en retenant l'adresse demandée", () => {
    renderAt("/accounts?tab=epargne", false)

    expect(screen.getByRole("heading", { name: "Connexion depuis /accounts?tab=epargne" })).toBeInTheDocument()
    expect(screen.queryByText("Mes comptes")).not.toBeInTheDocument()
  })

  it("avec un jeton expiré, redirige vers /login et oublie le jeton", () => {
    renderAt("/accounts", { expInMinutes: -5 })

    expect(screen.getByRole("heading", { name: "Connexion depuis /accounts" })).toBeInTheDocument()
    expect(safeStorage.getItem("token")).toBeNull()
  })

  it("avec un jeton valide, affiche le contenu protégé", () => {
    renderAt("/accounts", true)

    expect(screen.getByRole("heading", { name: "Mes comptes" })).toBeInTheDocument()
  })
})
