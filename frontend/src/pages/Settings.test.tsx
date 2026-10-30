/** Anciens `?tab=` des Paramètres : renommés ou redirigés vers la page qui les a repris. Cartes remplacées. */
import { screen } from "@testing-library/react"
import { Route, Routes } from "react-router-dom"
import { renderWithProviders } from "@/test/render"
import { LocationDisplay } from "@/test/LocationDisplay"
import Settings from "./Settings"

const { card } = vi.hoisted(() => ({ card: (name: string) => () => <p>Carte {name}</p> }))
vi.mock("@/components/settings/BackupCard", () => ({ BackupCard: card("sauvegarde") }))
vi.mock("@/components/settings/BudgetPeriodCard", () => ({ BudgetPeriodCard: card("période budgétaire") }))
vi.mock("@/components/settings/DangerZoneCard", () => ({ DangerZoneCard: card("zone de danger") }))
vi.mock("@/components/settings/DisplayCard", () => ({ DisplayCard: card("affichage") }))
vi.mock("@/components/settings/ExportCard", () => ({ ExportCard: card("export") }))
vi.mock("@/components/settings/ImportHistoryCard", () => ({ ImportHistoryCard: card("historique d'import") }))
vi.mock("@/components/settings/LoginActivityCard", () => ({ LoginActivityCard: card("connexions") }))
vi.mock("@/components/settings/McpAccessCard", () => ({ McpAccessCard: card("MCP") }))
vi.mock("@/components/settings/NotificationsTab", () => ({ NotificationsTab: card("notifications") }))
vi.mock("@/components/settings/PasskeyCard", () => ({ PasskeyCard: card("passkey") }))
vi.mock("@/components/settings/ProfileForm", () => ({ PasswordCard: card("mot de passe"), ProfileInfoCard: card("profil") }))
vi.mock("@/components/settings/TotpCard", () => ({ TotpCard: card("TOTP") }))

function renderSettings(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/settings" element={<><Settings /><LocationDisplay /></>} />
      <Route path="*" element={<LocationDisplay />} />
    </Routes>,
    { route, auth: true },
  )
}

const address = () => screen.getByRole("status", { name: "adresse" }).textContent
const activeTab = () => screen.getByRole("tab", { selected: true })

describe("Settings : onglets ?tab=", () => {
  it.each([
    ["categories", "/classement?tab=categories"],
    ["tags", "/classement?tab=tags"],
    ["merchants", "/classement?tab=merchants"],
    ["rules", "/classement?tab=rules"],
    ["transferts", "/audit?vue=virements"],
    ["transfers", "/audit?vue=virements"],
    ["import", "/accounts?import=1"],
  ])("?tab=%s (onglet parti) redirige vers %s", (tab, expected) => {
    renderSettings(`/settings?tab=${tab}`)

    expect(address()).toBe(expected)
    expect(screen.queryByRole("heading", { name: "Paramètres" })).not.toBeInTheDocument()
  })

  it.each([
    ["account", "Sécurité", "Carte mot de passe"],
    ["system", "Données", "Carte sauvegarde"],
  ])("?tab=%s (ancien nom) ouvre l'onglet %s", (tab, label, content) => {
    renderSettings(`/settings?tab=${tab}`)

    expect(activeTab()).toHaveTextContent(label)
    expect(screen.getByText(content)).toBeInTheDocument()
    expect(address()).toBe(`/settings?tab=${tab}`)
  })

  it.each([
    ["/settings", "Général"],
    ["/settings?tab=notifications", "Notifications"],
    ["/settings?tab=inconnu", "Général"],
  ])("%s ouvre l'onglet %s", (route, label) => {
    renderSettings(route)

    expect(activeTab()).toHaveTextContent(label)
  })

  it("changer d'onglet écrit ?tab= dans l'adresse", async () => {
    const { user } = renderSettings("/settings")

    await user.click(screen.getByRole("tab", { name: "Sécurité" }))

    expect(activeTab()).toHaveTextContent("Sécurité")
    expect(address()).toBe("/settings?tab=security")
  })
})
