/** Page d'un compte : chargement, création / édition / suppression d'une transaction (corps envoyé, toast, liste rechargée). */
import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Link, Route, Routes } from "react-router-dom"
import { makeAccount, makeTransaction } from "@/test/factories"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import type { Account, Transaction } from "./types"
import AccountDetail from "./index"

interface Backend {
  account: Account
  transactions: Transaction[]
  writes: { method: string; path: string; body: unknown }[]
  listCalls: number
}

/** Répond aux lectures de la page d'un compte courant et consigne les écritures sur /transactions. */
function serveAccount(transactions: Transaction[] = [], account = makeAccount({ id: 1, name: "Compte joint" })): Backend {
  const backend: Backend = { account, transactions, writes: [], listCalls: 0 }
  const record = async (request: Request) => {
    const text = await request.text()
    backend.writes.push({ method: request.method, path: new URL(request.url).pathname, body: text ? JSON.parse(text) : null })
  }
  server.use(
    http.get(apiUrl("/accounts/:id"), () => HttpResponse.json(backend.account)),
    http.get(apiUrl("/transactions/merchants"), () => HttpResponse.json(["Carrefour"])),
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    http.get(apiUrl("/transactions"), () => {
      backend.listCalls++
      return HttpResponse.json(backend.transactions)
    }),
    http.get(apiUrl("/analytics/timeseries"), () => HttpResponse.json([])),
    http.get(apiUrl("/categories"), () => HttpResponse.json([])),
    http.get(apiUrl("/tags"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/tags"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/account-flow-summary"), () => HttpResponse.json(null)),
    http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ configured: false, hourly_rate: null, work_hours_per_day: 7 })),
    http.post(apiUrl("/transactions"), async ({ request }) => {
      await record(request)
      return HttpResponse.json({ id: 99 })
    }),
    http.patch(apiUrl("/transactions/:id"), async ({ request }) => {
      await record(request)
      return HttpResponse.json({})
    }),
    http.delete(apiUrl("/transactions/:id"), async ({ request }) => {
      await record(request)
      return new HttpResponse(null, { status: 204 })
    }),
  )
  return backend
}

/** `WorkTimeProvider` : le menu d'une sortie affiche son prix en heures de travail. */
function renderAccount(route = "/accounts/1") {
  return renderWithProviders(
    <WorkTimeProvider>
      <Routes>
        <Route path="/accounts/:id" element={<AccountDetail />} />
      </Routes>
    </WorkTimeProvider>,
    { route, auth: true },
  )
}

/** La table de bureau (la liste mobile est aussi rendue, masquée par CSS). */
const desktopTable = () => screen.getByRole("table")
const dialog = () => screen.getByRole("dialog")

async function openRowMenu(user: ReturnType<typeof renderAccount>["user"], merchant: string) {
  const row = within(desktopTable()).getByText(merchant).closest("tr")!
  await user.click(within(row).getByTitle("Actions"))
}

describe("AccountDetail : chargement", () => {
  it("affiche le chargement puis le compte et ses transactions", async () => {
    serveAccount([makeTransaction({ id: 5, merchant: "Boulangerie" })])
    renderAccount()

    expect(screen.getByText("Chargement du compte...")).toBeInTheDocument()
    expect(await screen.findByRole("heading", { name: /Compte joint/ })).toBeInTheDocument()
    expect(within(desktopTable()).getByText("Boulangerie")).toBeInTheDocument()
  })

  it("échec du chargement : alerte avec le détail du serveur et « Réessayer », pas « Compte non trouvé »", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined)
    serveAccount([makeTransaction({ id: 5, merchant: "Boulangerie" })])
    server.use(http.get(apiUrl("/accounts/:id"), () => HttpResponse.json({ detail: "Base indisponible" }, { status: 500 }), { once: true }))
    const { user } = renderAccount()

    expect(await screen.findByRole("alert")).toHaveTextContent("Base indisponible")
    expect(screen.queryByText("Compte non trouvé")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Réessayer" }))
    expect(await screen.findByRole("heading", { name: /Compte joint/ })).toBeInTheDocument()
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("compte inexistant (404) : « Compte non trouvé », sans alerte", async () => {
    serveAccount()
    server.use(http.get(apiUrl("/accounts/:id"), () => HttpResponse.json({ detail: "Compte introuvable" }, { status: 404 })))
    renderAccount()

    expect(await screen.findByText("Compte non trouvé")).toBeInTheDocument()
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })


  it("changement de compte pendant un chargement lent : la réponse de l'ancien compte est ignorée", async () => {
    let releaseFirst = () => {}
    const firstPending = new Promise<void>((resolve) => (releaseFirst = resolve))
    serveAccount()
    server.use(
      http.get(apiUrl("/accounts/:id"), async ({ params }) => {
        if (params.id === "1") {
          await firstPending
          return HttpResponse.json(makeAccount({ id: 1, name: "Compte joint" }))
        }
        return HttpResponse.json(makeAccount({ id: 2, name: "Livret" }))
      }),
    )
    const { user } = renderWithProviders(
      <WorkTimeProvider>
        <Link to="/accounts/2">Autre compte</Link>
        <Routes>
          <Route path="/accounts/:id" element={<AccountDetail />} />
        </Routes>
      </WorkTimeProvider>,
      { route: "/accounts/1", auth: true },
    )

    await user.click(screen.getByRole("link", { name: "Autre compte" }))
    expect(await screen.findByRole("heading", { name: /Livret/ })).toBeInTheDocument()

    releaseFirst()
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(screen.getByRole("heading", { name: /Livret/ })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: /Compte joint/ })).not.toBeInTheDocument()
  })
})

describe("AccountDetail : transactions", () => {
  it("création : montant positif, type, date naïve sans Z, toast et liste rechargée", async () => {
    const backend = serveAccount()
    const { user } = renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })
    const callsBefore = backend.listCalls

    await user.click(screen.getByRole("button", { name: "Nouvelle opération" }))
    fireEvent.change(within(dialog()).getByLabelText("Date"), { target: { value: "2026-06-20T23:30" } })
    await user.click(within(dialog()).getByRole("combobox", { name: "Flux" }))
    await user.click(screen.getByRole("option", { name: "Entrée (+)" }))
    await user.type(within(dialog()).getByLabelText("Commerçant / Libellé"), "Remboursement")
    await user.type(within(dialog()).getByLabelText("Montant"), "12.5")
    backend.transactions = [makeTransaction({ id: 99, merchant: "Remboursement", type: "Entree", amount: 12.5 })]
    await user.click(within(dialog()).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Transaction ajoutée")).toBeInTheDocument()
    expect(backend.writes).toEqual([
      {
        method: "POST",
        path: "/transactions",
        body: expect.objectContaining({ account_id: 1, type: "Entree", merchant: "Remboursement", amount: 12.5, date: "2026-06-20T23:30:00" }),
      },
    ])
    expect(String((backend.writes[0].body as { date: string }).date)).not.toMatch(/Z$/)
    await waitFor(() => expect(within(desktopTable()).getByText("Remboursement")).toBeInTheDocument())
    expect(backend.listCalls).toBeGreaterThan(callsBefore)
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("création refusée sans libellé ni montant positif : rien n'est envoyé", async () => {
    const backend = serveAccount()
    const { user } = renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })

    await user.click(screen.getByRole("button", { name: "Nouvelle opération" }))
    await user.click(within(dialog()).getByRole("button", { name: "Enregistrer" }))
    expect(await screen.findByText("Veuillez saisir un commerçant ou un libellé")).toBeInTheDocument()

    await user.type(within(dialog()).getByLabelText("Commerçant / Libellé"), "Café")
    await user.type(within(dialog()).getByLabelText("Montant"), "0")
    await user.click(within(dialog()).getByRole("button", { name: "Enregistrer" }))
    expect(await screen.findByText("Le montant doit être un nombre supérieur à 0")).toBeInTheDocument()

    expect(backend.writes).toEqual([])
    expect(dialog()).toBeInTheDocument()
  })

  it("création en échec : message du serveur, le dialogue reste ouvert", async () => {
    serveAccount()
    server.use(http.post(apiUrl("/transactions"), () => HttpResponse.json({ detail: "Compte clôturé" }, { status: 400 })))
    const { user } = renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })

    await user.click(screen.getByRole("button", { name: "Nouvelle opération" }))
    await user.type(within(dialog()).getByLabelText("Commerçant / Libellé"), "Café")
    await user.type(within(dialog()).getByLabelText("Montant"), "3")
    await user.click(within(dialog()).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Compte clôturé")).toBeInTheDocument()
    expect(dialog()).toBeInTheDocument()
  })

  it("édition : dialogue prérempli, PATCH sans account_id, date naïve, toast", async () => {
    const backend = serveAccount([makeTransaction({ id: 5, merchant: "Boulangerie", amount: 8, original_amount: 8, date: "2026-06-15T07:45:00" })])
    const { user } = renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })

    await openRowMenu(user, "Boulangerie")
    await user.click(await screen.findByRole("menuitem", { name: "Modifier" }))
    expect(within(dialog()).getByRole("heading", { name: "Modifier l'opération" })).toBeInTheDocument()
    expect(within(dialog()).getByLabelText("Date")).toHaveValue("2026-06-15T07:45")
    expect(within(dialog()).getByLabelText("Montant")).toHaveValue(8)

    await user.clear(within(dialog()).getByLabelText("Montant"))
    await user.type(within(dialog()).getByLabelText("Montant"), "9.2")
    await user.click(within(dialog()).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Transaction modifiée")).toBeInTheDocument()
    expect(backend.writes).toEqual([
      { method: "PATCH", path: "/transactions/5", body: expect.objectContaining({ amount: 9.2, type: "Sortie", date: "2026-06-15T07:45:00" }) },
    ])
    expect(backend.writes[0].body).not.toHaveProperty("account_id")
  })

  it("suppression : confirmation (libellé, montant, date), DELETE, toast et liste rechargée", async () => {
    const backend = serveAccount([makeTransaction({ id: 5, merchant: "Boulangerie", amount: 8, date: "2026-06-15T07:45:00" })])
    const { user } = renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })

    await openRowMenu(user, "Boulangerie")
    await user.click(await screen.findByRole("menuitem", { name: "Supprimer" }))
    const confirmDialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(confirmDialog).toHaveTextContent(/Supprimer la transaction « Boulangerie » de 8,00\s€ \(15\/06\/2026\) \?/)
    backend.transactions = []
    await user.click(within(confirmDialog).getByRole("button", { name: /Supprimer|Confirmer/ }))

    expect(await screen.findByText("Transaction supprimée")).toBeInTheDocument()
    expect(backend.writes).toEqual([{ method: "DELETE", path: "/transactions/5", body: null }])
    await waitFor(() => expect(within(desktopTable()).queryByText("Boulangerie")).not.toBeInTheDocument())
  })

  it("suppression annulée : aucune requête", async () => {
    const backend = serveAccount([makeTransaction({ id: 5, merchant: "Boulangerie" })])
    const { user } = renderAccount()
    await screen.findByRole("heading", { name: /Compte joint/ })

    await openRowMenu(user, "Boulangerie")
    await user.click(await screen.findByRole("menuitem", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))

    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Confirmer" })).not.toBeInTheDocument())
    expect(backend.writes).toEqual([])
    expect(within(desktopTable()).getByText("Boulangerie")).toBeInTheDocument()
  })

})
