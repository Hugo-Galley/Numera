/** Passkeys : ajout et suppression exigent le mot de passe actuel (jeton de session volé). */
import { screen, waitFor } from "@testing-library/react"
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
})
