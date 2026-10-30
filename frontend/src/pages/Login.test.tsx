/** Connexion : identifiants, étape TOTP (`mfa_token`), limite de débit, redirection vers la page demandée. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { safeStorage } from "@/lib/storage"
import { apiUrl } from "@/test/handlers"
import { LocationDisplay } from "@/test/LocationDisplay"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { makeToken } from "@/test/token"
import Login from "./Login"

function renderLogin(route = "/login?from=/accounts") {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="*" element={<LocationDisplay />} />
    </Routes>,
    { route },
  )
}

const address = () => screen.queryByRole("status", { name: "adresse" })?.textContent

async function submitCredentials(user: ReturnType<typeof renderLogin>["user"], password = "secret") {
  await user.type(screen.getByLabelText("Utilisateur"), "admin")
  await user.type(screen.getByLabelText("Mot de passe"), password)
  await user.click(screen.getByRole("button", { name: "Se connecter" }))
}

describe("Login : mot de passe", () => {
  it("envoie le formulaire urlencodé, enregistre le jeton et redirige vers ?from=", async () => {
    const token = makeToken()
    const bodies: string[] = []
    server.use(
      http.post(apiUrl("/auth/token"), async ({ request }) => {
        bodies.push(await request.text())
        return HttpResponse.json({ access_token: token, token_type: "bearer" })
      }),
    )
    const { user } = renderLogin()

    await submitCredentials(user)

    await waitFor(() => expect(address()).toBe("/accounts"))
    expect(new URLSearchParams(bodies[0]).get("username")).toBe("admin")
    expect(new URLSearchParams(bodies[0]).get("password")).toBe("secret")
    expect(safeStorage.getItem("token")).toBe(token)
    expect(await screen.findByText("Connexion réussie")).toBeInTheDocument()
  })

  it("identifiants faux : message du backend, reste sur la page sans jeton", async () => {
    server.use(http.post(apiUrl("/auth/token"), () => HttpResponse.json({ detail: "Identifiants invalides" }, { status: 401 })))
    const { user } = renderLogin()

    await submitCredentials(user, "faux")

    expect(await screen.findByText("Identifiants invalides")).toBeInTheDocument()
    expect(address()).toBeUndefined()
    expect(safeStorage.getItem("token")).toBeNull()
    expect(screen.getByRole("button", { name: "Se connecter" })).toBeEnabled()
  })

  it("erreur sans détail exploitable : « Identifiants incorrects »", async () => {
    server.use(http.post(apiUrl("/auth/token"), () => new HttpResponse("oops", { status: 500 })))
    const { user } = renderLogin()

    await submitCredentials(user)

    expect(await screen.findByText("Identifiants incorrects")).toBeInTheDocument()
  })

  it("429 : message de limite de débit, quel que soit le détail", async () => {
    server.use(http.post(apiUrl("/auth/token"), () => HttpResponse.json({ detail: "Too many" }, { status: 429 })))
    const { user } = renderLogin()

    await submitCredentials(user)

    expect(await screen.findByText("Trop de tentatives. Réessaie dans quelques minutes.")).toBeInTheDocument()
    expect(screen.queryByText("Too many")).not.toBeInTheDocument()
  })

  it("le bouton est désactivé pendant l'envoi", async () => {
    let release!: () => void
    server.use(
      http.post(apiUrl("/auth/token"), async () => {
        await new Promise<void>((resolve) => (release = resolve))
        return HttpResponse.json({ detail: "Identifiants invalides" }, { status: 401 })
      }),
    )
    const { user } = renderLogin()

    await submitCredentials(user)

    expect(await screen.findByRole("button", { name: "Connexion..." })).toBeDisabled()
    release()
    expect(await screen.findByRole("button", { name: "Se connecter" })).toBeEnabled()
  })

  it("from externe (« //evil.com ») ignoré : redirection vers /", async () => {
    server.use(http.post(apiUrl("/auth/token"), () => HttpResponse.json({ access_token: makeToken() })))
    const { user } = renderLogin("/login?from=//evil.com")

    await submitCredentials(user)

    await waitFor(() => expect(address()).toBe("/"))
  })

  it("déjà connecté : redirige sans afficher le formulaire", () => {
    safeStorage.setItem("token", makeToken())
    renderLogin()

    expect(address()).toBe("/accounts")
    expect(screen.queryByLabelText("Mot de passe")).not.toBeInTheDocument()
  })
})

describe("Login : étape TOTP", () => {
  function mfaRequired() {
    return http.post(apiUrl("/auth/token"), () => HttpResponse.json({ mfa_required: true, mfa_token: "mfa-123" }))
  }

  it("mfa_token reçu : demande le code, puis envoie { mfa_token, code } et connecte", async () => {
    const token = makeToken()
    const bodies: unknown[] = []
    server.use(
      mfaRequired(),
      http.post(apiUrl("/auth/totp/login"), async ({ request }) => {
        bodies.push(await request.json())
        return HttpResponse.json({ access_token: token })
      }),
    )
    const { user } = renderLogin()

    await submitCredentials(user)
    expect(await screen.findByText("Vérification")).toBeInTheDocument()
    expect(safeStorage.getItem("token")).toBeNull()
    expect(screen.getByRole("button", { name: "Valider" })).toBeDisabled()

    await user.type(screen.getByLabelText("Code"), "123456")
    await user.click(screen.getByRole("button", { name: "Valider" }))

    await waitFor(() => expect(address()).toBe("/accounts"))
    expect(bodies).toEqual([{ mfa_token: "mfa-123", code: "123456" }])
    expect(safeStorage.getItem("token")).toBe(token)
  })

  it("code faux : message, champ vidé, reste sur l'étape code", async () => {
    server.use(mfaRequired(), http.post(apiUrl("/auth/totp/login"), () => HttpResponse.json({ detail: "Code invalide" }, { status: 401 })))
    const { user } = renderLogin()

    await submitCredentials(user)
    await user.type(await screen.findByLabelText("Code"), "000000")
    await user.click(screen.getByRole("button", { name: "Valider" }))

    expect(await screen.findByText("Code invalide")).toBeInTheDocument()
    expect(screen.getByLabelText("Code")).toHaveValue("")
    expect(safeStorage.getItem("token")).toBeNull()
  })

  it("429 sur le code : message de limite de débit", async () => {
    server.use(mfaRequired(), http.post(apiUrl("/auth/totp/login"), () => HttpResponse.json({}, { status: 429 })))
    const { user } = renderLogin()

    await submitCredentials(user)
    await user.type(await screen.findByLabelText("Code"), "123456")
    await user.click(screen.getByRole("button", { name: "Valider" }))

    expect(await screen.findByText("Trop de tentatives. Réessaie dans quelques minutes.")).toBeInTheDocument()
  })

  it("étape expirée (« Étape de connexion… ») : retour au formulaire mot de passe", async () => {
    server.use(
      mfaRequired(),
      http.post(apiUrl("/auth/totp/login"), () => HttpResponse.json({ detail: "Étape de connexion expirée" }, { status: 401 })),
    )
    const { user } = renderLogin()

    await submitCredentials(user)
    await user.type(await screen.findByLabelText("Code"), "123456")
    await user.click(screen.getByRole("button", { name: "Valider" }))

    expect(await screen.findByText("Étape de connexion expirée")).toBeInTheDocument()
    expect(screen.getByLabelText("Mot de passe")).toBeInTheDocument()
  })

  it("« Retour » revient au formulaire mot de passe", async () => {
    server.use(mfaRequired())
    const { user } = renderLogin()

    await submitCredentials(user)
    await user.click(await screen.findByRole("button", { name: "Retour" }))

    expect(screen.getByRole("button", { name: "Se connecter" })).toBeInTheDocument()
  })
})
