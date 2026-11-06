/** Cartes de réglages en anglais : passkeys, notifications, erreurs d'API traduites, durée relative. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { setLanguage } from "@/i18n"
import { api } from "@/lib/api"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { PasskeyCard } from "./PasskeyCard"
import { DangerZoneCard } from "./DangerZoneCard"

describe("réglages en anglais", () => {
  afterEach(() => setLanguage("fr"))

  it("carte passkeys : dates et message de navigateur non compatible", async () => {
    server.use(http.get(apiUrl("/auth/passkey"), () => HttpResponse.json([{ id: "c1", name: "iPhone", created_at: "2026-06-01T08:00:00", last_used_at: "2026-06-02T08:00:00" }])))
    await setLanguage("en")
    renderWithProviders(<PasskeyCard />, { auth: true })
    expect(await screen.findByText(/Added on/)).toBeInTheDocument()
    expect(screen.getByText(/used on/)).toBeInTheDocument()
    expect(screen.getByText("Passkeys are not supported by this browser.")).toBeInTheDocument()
  })

  it("zone de danger : le mot à taper reste EFFACER (contrat du backend)", async () => {
    await setLanguage("en")
    const { user } = renderWithProviders(<DangerZoneCard />, { auth: true })
    await user.click(screen.getByRole("button", { name: "Erase everything permanently" }))
    expect(await screen.findByText(/To confirm deletion, please type/)).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Type EFFACER here...")).toBeInTheDocument()
  })

  it("message d'erreur de l'API dans la langue de l'interface", async () => {
    server.use(http.get(apiUrl("/boom"), () => new HttpResponse(null, { status: 500 })))
    await setLanguage("en")
    await expect(api.get("/boom")).rejects.toThrow("Server error (500)")
    await setLanguage("fr")
    server.use(http.get(apiUrl("/boom2"), () => new HttpResponse(null, { status: 500 })))
    await waitFor(async () => { await expect(api.get("/boom2")).rejects.toThrow("Erreur du serveur (500)") })
  })
})
