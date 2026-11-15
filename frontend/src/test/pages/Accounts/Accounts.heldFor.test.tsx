/** Page Comptes : compte détenu pour un tiers (champ « Détenu pour », badge dans la liste). */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import Accounts from "@/pages/Accounts/index"

type Row = ReturnType<typeof makeAccount> & { active: boolean; held_for?: string | null }
const row = (overrides: Partial<Row>): Row => ({ ...makeAccount(), active: true, ...overrides })

function serveAccounts(initial: Row[]) {
  const writes: { method: string; body: Record<string, unknown> }[] = []
  server.use(
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json({ asset_classes: [], sectors: [], geographic_zones: [] })),
    http.get(apiUrl("/accounts"), () => HttpResponse.json(initial)),
    http.post(apiUrl("/accounts"), async ({ request }) => {
      const body = await request.json() as Record<string, unknown>
      writes.push({ method: "POST", body })
      return HttpResponse.json(row({ id: 99, ...body }))
    }),
    http.patch(apiUrl("/accounts/:id"), async ({ request }) => {
      writes.push({ method: "PATCH", body: await request.json() as Record<string, unknown> })
      return HttpResponse.json({})
    }),
  )
  return writes
}

const mine = row({ id: 1, name: "AXA Shareplan", type: "investissement", balance: 300 })
const hers = row({ id: 2, name: "AXA Shareplan Maman", type: "investissement", balance: 1200, held_for: "Maman" })
const view = () => renderWithProviders(<Accounts />, { route: "/accounts", auth: true })

describe("page Comptes : compte détenu pour un tiers", () => {
  it("la liste signale le compte tenu pour quelqu'un d'autre", async () => {
    serveAccounts([mine, hers])
    view()

    expect((await screen.findAllByText("Pour Maman")).length).toBeGreaterThan(0)
  })

  it("création : le nom du tiers part dans le corps, vide = compte à soi", async () => {
    const writes = serveAccounts([mine])
    const { user } = view()
    await screen.findAllByText("AXA Shareplan")
    await user.click(screen.getByRole("button", { name: "Ajouter un compte" }))
    const dialog = await screen.findByRole("dialog", { name: "Nouveau compte" })

    await user.type(within(dialog).getByLabelText("Nom du compte"), "AXA Maman")
    await user.type(within(dialog).getByLabelText("Détenu pour (optionnel)"), "Maman")
    await user.click(within(dialog).getByRole("button", { name: "Créer" }))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].body.held_for).toBe("Maman")
  })

  it("modification : effacer le nom du tiers rend le compte à soi", async () => {
    const writes = serveAccounts([hers])
    const { user } = view()
    await screen.findAllByText("AXA Shareplan Maman")
    const target = screen.getAllByRole("row").find((r) => within(r).queryByText("AXA Shareplan Maman"))!
    await user.click(within(target).getByRole("button", { name: "Modifier" }))
    const dialog = await screen.findByRole("dialog", { name: "Modifier le compte" })

    const field = within(dialog).getByLabelText("Détenu pour (optionnel)")
    expect(field).toHaveValue("Maman")
    await user.clear(field)
    await user.click(within(dialog).getByRole("button", { name: /Enregistrer|Mettre à jour|Sauvegarder/ }))

    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].body.held_for).toBeNull()
  })
})
