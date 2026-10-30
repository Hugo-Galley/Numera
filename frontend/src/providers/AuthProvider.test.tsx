import { act, screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { TOKEN_REFRESHED_EVENT } from "@/lib/api"
import { makeProfile } from "@/test/factories"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { makeToken } from "@/test/token"
import { useAuth } from "./AuthProvider"

function Session() {
  const { isAuthenticated, username, profile, token, login, logout } = useAuth()
  return (
    <div>
      <p>{isAuthenticated ? "connecté" : "déconnecté"}</p>
      <p>utilisateur : {username ?? "aucun"}</p>
      <p>profil : {profile ? "chargé" : "absent"}</p>
      <p data-testid="token">{token ?? ""}</p>
      <button onClick={() => login(makeToken({ sub: "nouveau" }))}>Connexion</button>
      <button onClick={logout}>Déconnexion</button>
    </div>
  )
}

const stored = () => window.localStorage.getItem("token")

describe("AuthProvider", () => {
  it("lit le jeton stocké au démarrage et charge le profil", async () => {
    const token = makeToken()
    const auths: (string | null)[] = []
    server.use(
      http.get(apiUrl("/admin/profile"), ({ request }) => {
        auths.push(request.headers.get("Authorization"))
        return HttpResponse.json(makeProfile({ username: "hugo" }))
      }),
    )

    renderWithProviders(<Session />, { auth: { token } })

    expect(screen.getByText("connecté")).toBeInTheDocument()
    // avant le profil, le nom vient du `sub` du jeton
    expect(screen.getByText("utilisateur : admin")).toBeInTheDocument()
    expect(await screen.findByText("utilisateur : hugo")).toBeInTheDocument()
    expect(auths).toEqual([`Bearer ${token}`])
  })

  it("ignore et supprime un jeton expiré, sans appeler le profil", () => {
    const calls = { count: 0 }
    server.use(
      http.get(apiUrl("/admin/profile"), () => {
        calls.count++
        return HttpResponse.json(makeProfile())
      }),
    )

    renderWithProviders(<Session />, { auth: { expInMinutes: -5 } })

    expect(screen.getByText("déconnecté")).toBeInTheDocument()
    expect(screen.getByText("utilisateur : aucun")).toBeInTheDocument()
    expect(stored()).toBeNull()
    expect(calls.count).toBe(0)
  })

  it("sans jeton : déconnecté", () => {
    renderWithProviders(<Session />)
    expect(screen.getByText("déconnecté")).toBeInTheDocument()
  })

  it("logout vide le stockage et la session", async () => {
    const { user } = renderWithProviders(<Session />, { auth: true })
    await screen.findByText("profil : chargé")

    await user.click(screen.getByRole("button", { name: "Déconnexion" }))

    expect(stored()).toBeNull()
    expect(screen.getByText("déconnecté")).toBeInTheDocument()
    expect(screen.getByText("profil : absent")).toBeInTheDocument()
  })

  it("login stocke le jeton et ouvre la session", async () => {
    const { user } = renderWithProviders(<Session />)

    await user.click(screen.getByRole("button", { name: "Connexion" }))

    expect(screen.getByText("connecté")).toBeInTheDocument()
    expect(stored()).toBe(screen.getByTestId("token").textContent)
    expect(await screen.findByText("profil : chargé")).toBeInTheDocument()
  })

  it.each([401, 403])("déconnecte si le profil répond %i", async (status) => {
    server.use(http.get(apiUrl("/admin/profile"), () => HttpResponse.json({ detail: "x" }, { status })))

    renderWithProviders(<Session />, { auth: true })

    expect(await screen.findByText("déconnecté")).toBeInTheDocument()
    expect(stored()).toBeNull()
  })

  it("reste connecté si le profil échoue autrement (500)", async () => {
    const calls = { count: 0 }
    server.use(
      http.get(apiUrl("/admin/profile"), () => {
        calls.count++
        return HttpResponse.json({ detail: "boom" }, { status: 500 })
      }),
    )

    renderWithProviders(<Session />, { auth: true })

    await waitFor(() => expect(calls.count).toBe(1))
    expect(screen.getByText("connecté")).toBeInTheDocument()
    expect(stored()).not.toBeNull()
  })

  it("adopte le jeton renouvelé par lib/api", async () => {
    renderWithProviders(<Session />, { auth: true })
    const renewed = makeToken({ expInMinutes: 120, sub: "renouvelé" })

    act(() => {
      window.dispatchEvent(new CustomEvent(TOKEN_REFRESHED_EVENT, { detail: renewed }))
    })

    expect(screen.getByTestId("token")).toHaveTextContent(renewed)
    await screen.findByText("profil : chargé")
  })

  it("déconnecte à la vérification périodique quand le jeton expire", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] })
    try {
      renderWithProviders(<Session />, { auth: { expInMinutes: 0.5 } })
      await screen.findByText("profil : chargé")
      expect(screen.getByText("connecté")).toBeInTheDocument()

      act(() => {
        vi.advanceTimersByTime(60_000)
      })

      expect(screen.getByText("déconnecté")).toBeInTheDocument()
      expect(stored()).toBeNull()
    } finally {
      vi.useRealTimers()
    }
  })
})
