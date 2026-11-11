/** Les écrans migrés s'affichent en anglais quand la langue est « en », et bougent avec le sélecteur. */
import { screen, within } from "@testing-library/react"
import { act } from "react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { setLanguage } from "@/i18n"
import { makeActionCenter } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { Sidebar } from "@/components/layout/Sidebar"
import Login from "@/pages/Login"
import NotFound from "@/pages/NotFound"

describe("écrans en anglais", () => {
  beforeEach(() => setLanguage("en"))
  afterEach(() => setLanguage("fr"))

  it("Connexion", () => {
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<Login />} />
      </Routes>,
      { route: "/login" },
    )
    expect(screen.getByText("Enter your credentials to sign in")).toBeInTheDocument()
    expect(screen.getByLabelText("Username")).toBeInTheDocument()
    expect(screen.getByLabelText("Password")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument()
  })

  it("Page introuvable", () => {
    renderWithProviders(<NotFound />)
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to the dashboard" })).toHaveAttribute("href", "/")
  })

  it("Menu : groupes, entrées et pastille d'actions urgentes", async () => {
    server.use(
      http.get(apiUrl("/analytics/actions"), () =>
        HttpResponse.json(makeActionCenter({ summary: { ...makeActionCenter().summary, high_priority: 1 } })),
      ),
    )
    renderWithProviders(<Sidebar />, { auth: true })

    expect(screen.getByText("Wealth")).toBeInTheDocument()
    const link = screen.getByRole("link", { name: /Action center/ })
    expect(await within(link).findByLabelText("1 urgent action")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument()
  })

  it("se met à jour quand la langue change en cours d'affichage", async () => {
    renderWithProviders(<NotFound />)
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument()
    await act(() => setLanguage("fr"))
    expect(screen.getByRole("heading", { name: "Page introuvable" })).toBeInTheDocument()
  })
})
