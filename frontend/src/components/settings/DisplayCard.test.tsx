import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { DisplayCard } from "@/components/settings/DisplayCard"
import { setLanguage } from "@/i18n"
import { safeStorage } from "@/lib/storage"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"

async function selectLanguage(user: ReturnType<typeof renderWithProviders>["user"], name: RegExp) {
  await user.click(screen.getByRole("combobox", { name: /Langue de l'interface|Interface language|Idioma de la interfaz/ }))
  await user.click(await screen.findByRole("option", { name }))
}

describe("DisplayCard : choix de la langue", () => {
  afterEach(() => setLanguage("fr"))

  it("propose Français et English avec leur drapeau, le français étant sélectionné", async () => {
    const { user } = renderWithProviders(<DisplayCard />, { auth: true })
    const trigger = screen.getByRole("combobox", { name: "Langue de l'interface" })
    expect(trigger).toHaveTextContent("Français")
    expect(trigger).toHaveTextContent("🇫🇷")
    await user.click(trigger)
    const listbox = await screen.findByRole("listbox")
    expect(within(listbox).getByRole("option", { name: /English/ })).toHaveTextContent("🇬🇧")
    expect(within(listbox).getByRole("option", { name: /Español/ })).toHaveTextContent("🇪🇸")
  })

  it("passe l'interface en anglais, retient le choix puis revient au français", async () => {
    const { user } = renderWithProviders(<DisplayCard />, { auth: true })

    await selectLanguage(user, /English/)
    expect(await screen.findByText("Display")).toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "Interface language" })).toBeInTheDocument()
    expect(screen.getByRole("radio", { name: "Dark" })).toBeInTheDocument()
    expect(safeStorage.getItem("language")).toBe("en")

    await selectLanguage(user, /Français/)
    expect(await screen.findByText("Affichage")).toBeInTheDocument()
    expect(safeStorage.getItem("language")).toBe("fr")
  })

  it("passe l'interface en espagnol", async () => {
    const { user } = renderWithProviders(<DisplayCard />, { auth: true })
    await selectLanguage(user, /Español/)
    expect(await screen.findByText("Visualización")).toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "Idioma de la interfaz" })).toHaveTextContent("Español")
    expect(safeStorage.getItem("language")).toBe("es")
  })

  it("enregistre la langue côté serveur pour les notifications envoyées sans requête", async () => {
    const bodies: unknown[] = []
    server.use(http.put(apiUrl("/notifications/settings"), async ({ request }) => {
      bodies.push(await request.json())
      return HttpResponse.json({})
    }))
    const { user } = renderWithProviders(<DisplayCard />, { auth: true })
    await selectLanguage(user, /English/)
    await waitFor(() => expect(bodies).toEqual([{ language: "en" }]))
  })
})
