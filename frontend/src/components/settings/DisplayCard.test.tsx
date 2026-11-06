import { screen, within } from "@testing-library/react"
import { DisplayCard } from "@/components/settings/DisplayCard"
import { setLanguage } from "@/i18n"
import { safeStorage } from "@/lib/storage"
import { renderWithProviders } from "@/test/render"

describe("DisplayCard : choix de la langue", () => {
  afterEach(() => setLanguage("fr"))

  it("propose Français et English, le français étant sélectionné", () => {
    renderWithProviders(<DisplayCard />, { auth: true })
    const group = screen.getByRole("radiogroup", { name: "Langue de l'interface" })
    expect(within(group).getByRole("radio", { name: "Français" })).toBeChecked()
    expect(within(group).getByRole("radio", { name: "English" })).not.toBeChecked()
  })

  it("passe l'interface en anglais, retient le choix puis revient au français", async () => {
    const { user } = renderWithProviders(<DisplayCard />, { auth: true })

    await user.click(screen.getByRole("radio", { name: "English" }))
    expect(await screen.findByText("Display")).toBeInTheDocument()
    expect(screen.getByRole("radiogroup", { name: "Interface language" })).toBeInTheDocument()
    expect(screen.getByRole("radio", { name: "Dark" })).toBeInTheDocument()
    expect(safeStorage.getItem("language")).toBe("en")

    await user.click(screen.getByRole("radio", { name: "Français" }))
    expect(await screen.findByText("Affichage")).toBeInTheDocument()
    expect(safeStorage.getItem("language")).toBe("fr")
  })
})
