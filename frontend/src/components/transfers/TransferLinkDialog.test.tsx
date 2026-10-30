/** Liaison manuelle d'un virement interne : candidates, liaison, contrepartie, « pas un virement », erreurs. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import type { TransferCandidate } from "@/types/transfers"
import { TransferLinkDialog } from "./TransferLinkDialog"

const accounts = [
  { id: 1, name: "Courant", type: "courant", currency: "EUR" },
  { id: 2, name: "Livret A", type: "epargne", currency: "EUR" },
]
const sortie = { id: 50, account_id: 1, type: "Sortie", merchant: "VIR LIVRET", amount: 200, currency: "EUR", date: "2026-06-10T09:00:00" }
const candidate: TransferCandidate = { sortie_id: 50, other_id: 77, type: "regular", account_id: 2, date: "2026-06-12T00:00:00", amount: 200, currency: "EUR", label: "VIR RECU", day_gap: 2, amount_gap_pct: 0 }

function setup(candidates: TransferCandidate[] = [candidate]) {
  const posts: { path: string; search: string; body: unknown }[] = []
  server.use(
    http.get(apiUrl("/transactions/50/transfer-candidates"), () => HttpResponse.json(candidates)),
    http.post(apiUrl("/transactions/*"), async ({ request }) => {
      const url = new URL(request.url)
      posts.push({ path: url.pathname, search: url.search, body: await request.json() })
      return HttpResponse.json({})
    }),
  )
  const onDone = vi.fn()
  const onOpenChange = vi.fn()
  const view = renderWithProviders(<TransferLinkDialog open transaction={sortie} accounts={accounts} onOpenChange={onOpenChange} onDone={onDone} />, { auth: true })
  return { ...view, posts, onDone, onOpenChange }
}

describe("TransferLinkDialog", () => {
  it("lie la sortie à une candidate avec le type de virement", async () => {
    const { user, posts, onDone, onOpenChange } = setup()

    await user.click(await screen.findByRole("button", { name: "Lier" }))

    expect(await screen.findByText("Virement lié")).toBeInTheDocument()
    expect(posts).toEqual([{ path: "/transactions/50/link/77", search: "?type=regular", body: {} }])
    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(onDone).toHaveBeenCalled()
  })

  it("crée la contrepartie sur le compte choisi (bouton inactif sans compte)", async () => {
    const { user, posts } = setup([])
    expect(await screen.findByText(/Aucune candidate/)).toBeInTheDocument()

    const create = screen.getByRole("button", { name: "Créer et lier" })
    expect(create).toBeDisabled()
    await user.click(screen.getAllByRole("combobox")[1])
    await user.click(await screen.findByRole("option", { name: "Livret A" }))
    await user.click(create)

    expect(await screen.findByText("Contrepartie créée et liée")).toBeInTheDocument()
    expect(posts).toEqual([{ path: "/transactions/50/transfer-counterpart", search: "", body: { account_id: 2 } }])
  })

  it("« Ce n'est pas un virement » ignore la ligne", async () => {
    const { user, posts } = setup()

    await user.click(await screen.findByRole("button", { name: "Ce n'est pas un virement" }))

    expect(await screen.findByText("Cette ligne ne sera plus proposée comme virement")).toBeInTheDocument()
    expect(posts[0]).toMatchObject({ path: "/transactions/50/ignore" })
  })

  it("garde le dialogue ouvert si la liaison échoue", async () => {
    const { user, onOpenChange, onDone } = setup()
    server.use(http.post(apiUrl("/transactions/50/link/77"), () => HttpResponse.json({ detail: "Déjà lié" }, { status: 409 })))

    await user.click(await screen.findByRole("button", { name: "Lier" }))

    expect(await screen.findByText("Échec de la liaison")).toBeInTheDocument()
    expect(onOpenChange).not.toHaveBeenCalled()
    expect(onDone).not.toHaveBeenCalled()
  })
})
