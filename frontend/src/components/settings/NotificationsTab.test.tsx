/** Réglages des notifications : chargement, enregistrement (seulement si modifié), test d'un canal, erreurs. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { NotificationsTab } from "./NotificationsTab"

type Body = Record<string, unknown>

const settings = {
  ntfy_enabled: false,
  ntfy_server: "https://ntfy.sh",
  ntfy_topic: "",
  ntfy_token: "",
  telegram_enabled: false,
  telegram_bot_token: "",
  telegram_chat_id: "",
  min_severity: "medium",
  weekly_digest: true,
  hide_amounts: false,
  public_url: "",
}

function setup(onPut: (body: Body) => Response | Promise<Response> = (body) => HttpResponse.json(body)) {
  const calls: { method: string; path: string; body: Body }[] = []
  server.use(
    http.get(apiUrl("/notifications/settings"), () => HttpResponse.json(settings)),
    http.put(apiUrl("/notifications/settings"), async ({ request }) => {
      const body = (await request.json()) as Body
      calls.push({ method: "PUT", path: "/notifications/settings", body })
      return onPut(body)
    }),
    http.post(apiUrl("/notifications/test"), async ({ request }) => {
      calls.push({ method: "POST", path: "/notifications/test", body: (await request.json()) as Body })
      return HttpResponse.json({})
    }),
  )
  const view = renderWithProviders(<NotificationsTab />, { auth: true })
  return { ...view, calls }
}

/** Ré-authentification exigée quand une destination d'envoi change. */
async function confirmPassword(user: ReturnType<typeof setup>["user"], password = "admin") {
  await user.type(await screen.findByLabelText("Mot de passe actuel"), password)
  await user.click(screen.getByRole("button", { name: "Confirmer" }))
}

describe("NotificationsTab", () => {
  it("affiche une erreur avec « Réessayer » si les réglages ne chargent pas", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined)
    setup()
    server.use(http.get(apiUrl("/notifications/settings"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))

    expect(await screen.findByText("Impossible de charger les réglages des notifications.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument()
  })

  it("n'active « Enregistrer » qu'après une modification, puis envoie tous les réglages", async () => {
    const { user, calls } = setup()
    const save = await screen.findByRole("button", { name: "Enregistrer" })
    expect(save).toBeDisabled()
    expect(screen.getAllByRole("button", { name: /Envoyer un test/ })[0]).toBeDisabled()

    await user.type(screen.getByLabelText("Sujet"), "numera-a8f3k2")
    await user.click(screen.getByRole("switch", { name: "Activer ntfy" }))
    await user.click(save)
    await confirmPassword(user)

    expect(await screen.findByText("Réglages des notifications enregistrés")).toBeInTheDocument()
    expect(calls).toEqual([
      { method: "PUT", path: "/notifications/settings", body: { ...settings, ntfy_topic: "numera-a8f3k2", ntfy_enabled: true, current_password: "admin" } },
    ])
    await waitFor(() => expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled())
  })

  it("« Enregistrer et tester » enregistre d'abord les modifications puis envoie le test", async () => {
    const { user, calls } = setup()
    await user.type(await screen.findByLabelText("Sujet"), "numera-a8f3k2")

    await user.click(screen.getAllByRole("button", { name: /Enregistrer et tester/ })[0])
    await confirmPassword(user)

    expect(await screen.findByText("Message de test envoyé sur ntfy")).toBeInTheDocument()
    expect(calls.map((c) => `${c.method} ${c.path}`)).toEqual(["PUT /notifications/settings", "POST /notifications/test"])
    expect(calls[1].body).toEqual({ channel: "ntfy" })
  })

  it("n'envoie pas le test si l'enregistrement échoue, et affiche l'erreur du serveur", async () => {
    const { user, calls } = setup(() => HttpResponse.json({ detail: "Sujet invalide" }, { status: 422 }))
    await user.type(await screen.findByLabelText("Jeton du bot"), "123:abc")
    await user.type(screen.getByLabelText("Chat id"), "42")

    await user.click(screen.getAllByRole("button", { name: /Enregistrer et tester/ })[1])
    await confirmPassword(user)

    expect(await screen.findByText("Sujet invalide")).toBeInTheDocument()
    expect(calls.map((c) => c.path)).toEqual(["/notifications/settings"])
  })

  it("affiche « Enregistrement… » désactivé pendant l'envoi", async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    const { user, calls } = setup(async (body) => {
      await gate
      return HttpResponse.json(body)
    })
    await user.type(await screen.findByLabelText("Adresse de votre instance Numera (facultatif)"), "https://numera.test")

    await user.click(screen.getByRole("button", { name: "Enregistrer" }))
    await confirmPassword(user)
    const busy = await screen.findByRole("button", { name: "Enregistrement…" })
    expect(busy).toBeDisabled()
    release()
    await screen.findByText("Réglages des notifications enregistrés")
    expect(calls).toHaveLength(1)
  })

  it("« Annuler » rétablit les réglages enregistrés", async () => {
    const { user } = setup()
    const topic = await screen.findByLabelText("Sujet")
    await user.type(topic, "brouillon")

    await user.click(screen.getByRole("button", { name: "Annuler" }))

    expect(topic).toHaveValue("")
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled()
  })

  it("un réglage non sensible s'enregistre sans mot de passe", async () => {
    const { user, calls } = setup()
    await user.click(await screen.findByRole("switch", { name: "Activer ntfy" }))
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    await screen.findByText("Réglages des notifications enregistrés")
    expect(screen.queryByLabelText("Mot de passe actuel")).not.toBeInTheDocument()
    expect(calls[0].body).not.toHaveProperty("current_password")
  })

  it("annuler la ré-authentification n'envoie rien", async () => {
    const { user, calls } = setup()
    await user.type(await screen.findByLabelText("Sujet"), "pirate")
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))
    await user.click(await screen.findByRole("button", { name: "Annuler", hidden: false }))

    expect(calls).toEqual([])
  })
})
