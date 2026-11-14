/** Passkeys : ajout et suppression exigent le mot de passe actuel (jeton de session volé). */
import { screen, waitFor } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { PasskeyCard } from "@/components/settings/PasskeyCard"

const passkey = { id: "cred-1", name: "iPhone", created_at: "2026-06-01T08:00:00", last_used_at: null }

function setup() {
  const calls: { method: string; path: string; body: unknown }[] = []
  server.use(
    http.get(apiUrl("/auth/passkey"), () => HttpResponse.json([passkey])),
    http.delete(apiUrl("/auth/passkey/:id"), async ({ request, params }) => {
      calls.push({ method: "DELETE", path: `/auth/passkey/${params.id}`, body: await request.json() })
      return HttpResponse.json({ ok: true })
    }),
  )
  return { ...renderWithProviders(<PasskeyCard />, { auth: true }), calls }
}

describe("PasskeyCard", () => {
  it("suppression : confirme, demande le mot de passe actuel et l'envoie avec le DELETE", async () => {
    const { user, calls } = setup()
    await user.click(await screen.findByRole("button", { name: "Supprimer iPhone" }))
    await user.click(await screen.findByRole("button", { name: /Supprimer|Confirmer|Oui/ }))

    await user.type(await screen.findByLabelText("Mot de passe actuel"), "admin")
    await user.click(screen.getByRole("button", { name: "Confirmer" }))

    await waitFor(() => expect(calls).toEqual([{ method: "DELETE", path: "/auth/passkey/cred-1", body: { current_password: "admin" } }]))
  })

  describe("ajout d'une passkey", () => {
    const options = { challenge: "AQID", user: { id: "AQID", name: "admin" }, rp: { name: "Numera" } }
    const credential = { id: "new-cred", type: "public-key", rawId: Uint8Array.from([1]).buffer, response: { clientDataJSON: Uint8Array.from([2]).buffer, attestationObject: Uint8Array.from([3]).buffer } }

    function setupRegister(create: () => Promise<unknown>) {
      const posts: { path: string; body: unknown }[] = []
      server.use(
        http.get(apiUrl("/auth/passkey"), () => HttpResponse.json([])),
        http.post(apiUrl("/auth/passkey/register/options"), async ({ request }) => { posts.push({ path: "options", body: await request.json() }); return HttpResponse.json({ options, state: "st-1" }) }),
        http.post(apiUrl("/auth/passkey/register/verify"), async ({ request }) => { posts.push({ path: "verify", body: await request.json() }); return HttpResponse.json({ ok: true }) }),
      )
      vi.stubGlobal("PublicKeyCredential", class {})
      Object.defineProperty(navigator, "credentials", { value: { create: vi.fn(create), get: vi.fn() }, configurable: true })
      return { posts, ...renderWithProviders(<PasskeyCard />, { auth: true }) }
    }
    afterEach(() => {
      Reflect.deleteProperty(navigator, "credentials")
      vi.unstubAllGlobals()
    })

    const askPassword = async (user: ReturnType<typeof renderWithProviders>["user"]) => {
      await user.click(await screen.findByRole("button", { name: "Ajouter une passkey" }))
      await user.type(await screen.findByLabelText("Mot de passe actuel"), "admin")
      await user.click(screen.getByRole("button", { name: "Confirmer" }))
    }

    it("mot de passe demandé, options du serveur, geste biométrique, puis enregistrement de la passkey", async () => {
      const { user, posts } = setupRegister(async () => credential)

      await askPassword(user)

      await waitFor(() => expect(posts.map((p) => p.path)).toEqual(["options", "verify"]))
      expect(posts[0].body).toEqual({ current_password: "admin" })
      expect(posts[1].body).toMatchObject({ state: "st-1", current_password: "admin", credential: { id: "new-cred", rawId: "AQ" } })
      expect(await screen.findByText("Passkey enregistrée")).toBeInTheDocument()
    })

    it("geste annulé sur l'appareil (NotAllowedError) : aucun message d'erreur, rien n'est enregistré", async () => {
      const { user, posts } = setupRegister(async () => { throw Object.assign(new Error("annulé"), { name: "NotAllowedError" }) })

      await askPassword(user)

      await waitFor(() => expect(posts.map((p) => p.path)).toEqual(["options"]))
      expect(screen.queryByText("annulé")).not.toBeInTheDocument()
      expect(screen.queryByText("Passkey enregistrée")).not.toBeInTheDocument()
    })

    it("autre erreur de l'appareil : son message est affiché", async () => {
      const { user } = setupRegister(async () => { throw new Error("Clé de sécurité absente") })

      await askPassword(user)

      expect(await screen.findByText("Clé de sécurité absente")).toBeInTheDocument()
    })

    it("navigateur sans WebAuthn : message d'information à la place du bouton", async () => {
      server.use(http.get(apiUrl("/auth/passkey"), () => HttpResponse.json([])))
      vi.stubGlobal("PublicKeyCredential", undefined)
      renderWithProviders(<PasskeyCard />, { auth: true })

      expect(await screen.findByText("Passkeys non prises en charge par ce navigateur.")).toBeInTheDocument()
      expect(screen.queryByRole("button", { name: "Ajouter une passkey" })).not.toBeInTheDocument()
    })
  })
})
