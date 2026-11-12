/** Zone de danger : effacement complet de la base, protégé par un mot-clé à taper et le mot de passe actuel. */
import { screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { DangerZoneCard } from "@/components/settings/DangerZoneCard"

const reload = vi.fn()

beforeEach(() => {
  reload.mockReset()
  vi.stubGlobal("location", { ...window.location, reload })
})
afterEach(() => vi.unstubAllGlobals())

async function openDialog() {
  const view = renderWithProviders(<DangerZoneCard />, { auth: true })
  await view.user.click(screen.getByRole("button", { name: /Tout effacer définitivement/ }))
  return { ...view, dialog: await screen.findByRole("dialog") }
}
const confirmButton = (dialog: HTMLElement) => within(dialog).getByRole("button", { name: "Confirmer la suppression totale" })

describe("DangerZoneCard", () => {
  it("la carte annonce que l'action est irréversible ; la fenêtre ne s'ouvre qu'au clic", () => {
    renderWithProviders(<DangerZoneCard />, { auth: true })

    expect(screen.getByText("Zone de danger")).toBeInTheDocument()
    expect(screen.getByText("Ces actions sont irréversibles.")).toBeInTheDocument()
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("« Confirmer » reste désactivé sans le mot EFFACER exact ET sans mot de passe", async () => {
    const { user, dialog } = await openDialog()
    expect(confirmButton(dialog)).toBeDisabled()

    await user.type(within(dialog).getByPlaceholderText("Tapez EFFACER ici..."), "effacer")
    await user.type(within(dialog).getByLabelText("Mot de passe actuel"), "admin")
    expect(confirmButton(dialog)).toBeDisabled() // casse différente

    await user.clear(within(dialog).getByPlaceholderText("Tapez EFFACER ici..."))
    await user.type(within(dialog).getByPlaceholderText("Tapez EFFACER ici..."), "EFFACER")
    expect(confirmButton(dialog)).toBeEnabled()

    await user.clear(within(dialog).getByLabelText("Mot de passe actuel"))
    expect(confirmButton(dialog)).toBeDisabled()
  })

  it("confirmation : POST avec le code et le mot de passe, message de réussite, rechargement de la page", async () => {
    let body: unknown
    server.use(http.post(apiUrl("/admin/reset-database"), async ({ request }) => { body = await request.json(); return HttpResponse.json({}) }))
    const { user, dialog } = await openDialog()

    await user.type(within(dialog).getByPlaceholderText("Tapez EFFACER ici..."), "EFFACER")
    await user.type(within(dialog).getByLabelText("Mot de passe actuel"), "admin")
    await user.click(confirmButton(dialog))

    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1))
    expect(body).toEqual({ confirm: true, confirmation_code: "EFFACER", current_password: "admin" })
    expect(await screen.findByText("Base réinitialisée avec succès")).toBeInTheDocument()
  })

  it("refus du serveur (mot de passe incorrect) : message d'erreur, pas de rechargement, fenêtre ouverte", async () => {
    server.use(http.post(apiUrl("/admin/reset-database"), () => HttpResponse.json({ detail: "Mot de passe incorrect" }, { status: 403 })))
    const { user, dialog } = await openDialog()

    await user.type(within(dialog).getByPlaceholderText("Tapez EFFACER ici..."), "EFFACER")
    await user.type(within(dialog).getByLabelText("Mot de passe actuel"), "mauvais")
    await user.click(confirmButton(dialog))

    expect(await screen.findByText("Mot de passe incorrect")).toBeInTheDocument()
    expect(reload).not.toHaveBeenCalled()
    expect(screen.getByRole("dialog")).toBeInTheDocument()
  })

  it("« Annuler » ferme la fenêtre sans rien envoyer et vide les champs à la réouverture", async () => {
    let posted = false
    server.use(http.post(apiUrl("/admin/reset-database"), () => { posted = true; return HttpResponse.json({}) }))
    const { user, dialog } = await openDialog()
    await user.type(within(dialog).getByPlaceholderText("Tapez EFFACER ici..."), "EFFACER")

    await user.click(within(dialog).getByRole("button", { name: "Annuler" }))
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    await user.click(screen.getByRole("button", { name: /Tout effacer définitivement/ }))

    expect(within(await screen.findByRole("dialog")).getByPlaceholderText("Tapez EFFACER ici...")).toHaveValue("")
    expect(posted).toBe(false)
  })
})
