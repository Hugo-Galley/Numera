/** Règles de virement interne : liste, création / modification, activation, suppression, rattrapage du passé. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { TransferRulesSection } from "@/components/classement/TransferRulesSection"
import type { TransferApplyResult, TransferRule } from "@/types/transfers"

const courant = makeAccount({ id: 1, name: "Compte courant" })
const livret = makeAccount({ id: 2, name: "Livret A", type: "epargne" })
const pea = makeAccount({ id: 3, name: "PEA", type: "investissement" })

const rule: TransferRule = { id: 10, source_account_id: 1, dest_account_id: 2, pattern: "LIVRET", amount: 500, amount_tolerance_pct: 2, day_tolerance: 4, is_active: true }
const loose: TransferRule = { id: 11, source_account_id: 1, dest_account_id: 3, pattern: null, amount: null, amount_tolerance_pct: 1, day_tolerance: 5, is_active: false }

type Write = { method: string; path: string; body: unknown }

function serve({ rules = [rule, loose], apply = { dry_run: true, count: 0, pairs: [] } as TransferApplyResult } = {}) {
  const writes: Write[] = []
  let loads = 0
  const note = async (request: Request, path: string) => {
    const text = await request.text()
    writes.push({ method: request.method, path, body: text ? JSON.parse(text) : null })
  }
  server.use(
    http.get(apiUrl("/transfer-rules"), () => { loads += 1; return HttpResponse.json(rules) }),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([courant, livret, pea])),
    http.post(apiUrl("/transfer-rules/apply"), async ({ request }) => {
      const dry = new URL(request.url).searchParams.get("dry_run") === "true"
      await note(request, `/transfer-rules/apply${dry ? "?dry_run=true" : ""}`)
      return HttpResponse.json(dry ? apply : { ...apply, dry_run: false })
    }),
    http.post(apiUrl("/transfer-rules"), async ({ request }) => { await note(request, "/transfer-rules"); return HttpResponse.json({ id: 99 }) }),
    http.patch(apiUrl("/transfer-rules/:id"), async ({ request, params }) => { await note(request, `/transfer-rules/${params.id}`); return HttpResponse.json({}) }),
    http.delete(apiUrl("/transfer-rules/:id"), async ({ request, params }) => { await note(request, `/transfer-rules/${params.id}`); return new HttpResponse(null, { status: 204 }) }),
  )
  return { writes, loads: () => loads }
}

const view = () => renderWithProviders(<TransferRulesSection />, { auth: true })
/** La carte d'une règle, repérée par un morceau de sa description. */
const ruleCard = (description: RegExp) => within(screen.getByText(description).closest(".rounded-xl") as HTMLElement)

describe("TransferRulesSection : liste", () => {
  it("décrit chaque règle : comptes, libellé, montant approché et tolérances", async () => {
    serve()
    view()

    expect(await screen.findByText("Règles de virement")).toBeInTheDocument()
    expect(screen.getAllByText("Compte courant")).toHaveLength(2)
    expect(screen.getByText(/Libellé contient « LIVRET »/)).toBeInTheDocument()
    expect(screen.getByText(/≈ 500,00/)).toBeInTheDocument()
    expect(screen.getByText(/Tout libellé/)).toBeInTheDocument()
    expect(screen.getByText(/Tout montant/)).toBeInTheDocument()
  })

  it("aucune règle : message d'invitation et « Rattraper le passé » désactivé", async () => {
    serve({ rules: [] })
    view()

    expect(await screen.findByText(/Aucune règle\. Créez-en une/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Rattraper le passé" })).toBeDisabled()
  })

  it("chargement en échec : message d'erreur", async () => {
    server.use(
      http.get(apiUrl("/transfer-rules"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })),
      http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
    )
    view()

    expect(await screen.findByText("Erreur lors du chargement des règles de virement")).toBeInTheDocument()
  })
})

describe("TransferRulesSection : création et modification", () => {
  it("sans compte source et destination : message, aucune requête", async () => {
    const { writes } = serve()
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(screen.getByRole("button", { name: "Nouvelle règle" }))
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Créer la règle" }))

    expect(await screen.findByText("Choisissez un compte source et un compte destination")).toBeInTheDocument()
    expect(writes).toEqual([])
  })

  it("création : POST avec comptes, libellé, montant (virgule) et tolérances", async () => {
    const { writes, loads } = serve()
    const { user } = view()
    await screen.findByText("Règles de virement")
    const before = loads()

    await user.click(screen.getByRole("button", { name: "Nouvelle règle" }))
    const dialog = await screen.findByRole("dialog", { name: "Nouvelle règle de virement" })
    const [source, dest] = within(dialog).getAllByRole("combobox")
    await user.click(source)
    await user.click(await screen.findByRole("option", { name: "Compte courant" }))
    await user.click(dest)
    expect(screen.queryByRole("option", { name: "Compte courant" })).not.toBeInTheDocument() // le compte source est exclu de la destination
    await user.click(await screen.findByRole("option", { name: "Livret A" }))
    await user.type(within(dialog).getByLabelText("Le libellé de la sortie contient (optionnel)"), "  EPARGNE  ")
    await user.type(within(dialog).getByLabelText("Montant (optionnel)"), "250,5")
    await user.clear(within(dialog).getByLabelText("Tolérance montant %"))
    await user.type(within(dialog).getByLabelText("Tolérance montant %"), "3")
    await user.clear(within(dialog).getByLabelText("Tolérance jours"))
    await user.type(within(dialog).getByLabelText("Tolérance jours"), "7")
    await user.click(within(dialog).getByRole("button", { name: "Créer la règle" }))

    await waitFor(() => expect(writes).toEqual([{ method: "POST", path: "/transfer-rules", body: { source_account_id: 1, dest_account_id: 2, pattern: "EPARGNE", amount: 250.5, amount_tolerance_pct: 3, day_tolerance: 7 } }]))
    expect(await screen.findByText("Règle créée")).toBeInTheDocument()
    await waitFor(() => expect(loads()).toBeGreaterThan(before))
  })

  it("création refusée : message d'erreur", async () => {
    serve()
    server.use(http.post(apiUrl("/transfer-rules"), () => HttpResponse.json({ detail: "KO" }, { status: 422 })))
    const { user } = view()
    await screen.findByText("Règles de virement")
    await user.click(screen.getByRole("button", { name: "Nouvelle règle" }))
    const dialog = await screen.findByRole("dialog")
    const [source, dest] = within(dialog).getAllByRole("combobox")
    await user.click(source)
    await user.click(await screen.findByRole("option", { name: "Compte courant" }))
    await user.click(dest)
    await user.click(await screen.findByRole("option", { name: "PEA" }))

    await user.click(within(dialog).getByRole("button", { name: "Créer la règle" }))

    expect(await screen.findByText("Impossible de créer la règle")).toBeInTheDocument()
  })

  it("modification : dialogue prérempli, PATCH, rappel que le passé n'est pas modifié", async () => {
    const { writes } = serve()
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(ruleCard(/LIVRET/).getByRole("button", { name: "Modifier la règle" }))
    const dialog = await screen.findByRole("dialog", { name: "Modifier la règle de virement" })
    expect(within(dialog).getByLabelText("Le libellé de la sortie contient (optionnel)")).toHaveValue("LIVRET")
    expect(within(dialog).getByLabelText("Montant (optionnel)")).toHaveValue("500")
    expect(dialog).toHaveTextContent("Les virements déjà liés ne changent pas")
    await user.clear(within(dialog).getByLabelText("Montant (optionnel)"))
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "PATCH", path: "/transfer-rules/10", body: { source_account_id: 1, dest_account_id: 2, pattern: "LIVRET", amount: null, amount_tolerance_pct: 2, day_tolerance: 4 } }]))
    expect(await screen.findByText("Règle modifiée")).toBeInTheDocument()
  })

  it("modification refusée : message d'erreur propre à la modification", async () => {
    serve()
    server.use(http.patch(apiUrl("/transfer-rules/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 422 })))
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(ruleCard(/LIVRET/).getByRole("button", { name: "Modifier la règle" }))
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Impossible de modifier la règle")).toBeInTheDocument()
  })
})

describe("TransferRulesSection : activation, suppression, rattrapage", () => {
  it("l'interrupteur inverse is_active", async () => {
    const { writes } = serve()
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(ruleCard(/Tout libellé/).getByRole("switch"))

    await waitFor(() => expect(writes).toEqual([{ method: "PATCH", path: "/transfer-rules/11", body: { is_active: true } }]))
  })

  it("interrupteur refusé : message d'erreur", async () => {
    serve()
    server.use(http.patch(apiUrl("/transfer-rules/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(ruleCard(/Tout libellé/).getByRole("switch"))

    expect(await screen.findByText("Échec de l'action")).toBeInTheDocument()
  })

  it("suppression : confirmation (les virements liés restent liés), DELETE ; annulée : rien", async () => {
    const { writes } = serve()
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(ruleCard(/Tout libellé/).getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Annuler" }))
    expect(writes).toEqual([])

    await user.click(ruleCard(/Tout libellé/).getByRole("button", { name: "Supprimer" }))
    const dialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(dialog).toHaveTextContent("Les virements déjà liés restent liés")
    await user.click(within(dialog).getByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(writes).toEqual([{ method: "DELETE", path: "/transfer-rules/11", body: null }]))
    expect(await screen.findByText("Règle supprimée")).toBeInTheDocument()
  })

  it("suppression refusée : message d'erreur", async () => {
    serve()
    server.use(http.delete(apiUrl("/transfer-rules/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(ruleCard(/Tout libellé/).getByRole("button", { name: "Supprimer" }))
    await user.click(within(await screen.findByRole("dialog", { name: "Confirmer" })).getByRole("button", { name: "Supprimer" }))

    expect(await screen.findByText("Échec de la suppression")).toBeInTheDocument()
  })

  it("rattrapage sans virement à lier : simple information, aucun dialogue", async () => {
    const { writes } = serve()
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(screen.getByRole("button", { name: "Rattraper le passé" }))

    expect(await screen.findByText("Aucun virement à rattraper avec les règles actives")).toBeInTheDocument()
    expect(writes).toEqual([{ method: "POST", path: "/transfer-rules/apply?dry_run=true", body: {} }])
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("rattrapage : aperçu des couples puis application, nombre de virements liés annoncé", async () => {
    const pairs = [{ rule_id: 10, kind: "regular" as const, day_gap: 1, sortie: { id: 1, account_id: 1, date: "2026-05-02T00:00:00", amount: 500, currency: "EUR", label: "VIR LIVRET" }, entree: { id: 2, account_id: 2, date: "2026-05-03T00:00:00", amount: 500, currency: "EUR", label: "Versement" } }]
    const { writes } = serve({ apply: { dry_run: true, count: 1, pairs } })
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(screen.getByRole("button", { name: "Rattraper le passé" }))
    const dialog = await screen.findByRole("dialog", { name: "Rattraper le passé" })
    expect(dialog).toHaveTextContent("1 virement sera lié sur tout l'historique")
    expect(dialog).toHaveTextContent("Compte courant")
    expect(dialog).toHaveTextContent("Livret A")
    await user.click(within(dialog).getByRole("button", { name: "Lier ces virements" }))

    await waitFor(() => expect(writes.map((w) => w.path)).toEqual(["/transfer-rules/apply?dry_run=true", "/transfer-rules/apply"]))
    expect(await screen.findByText("1 virement lié")).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Rattraper le passé" })).not.toBeInTheDocument())
  })

  it("aperçu refusé : message d'erreur ; application refusée : message d'erreur", async () => {
    serve()
    server.use(http.post(apiUrl("/transfer-rules/apply"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = view()
    await screen.findByText("Règles de virement")

    await user.click(screen.getByRole("button", { name: "Rattraper le passé" }))

    expect(await screen.findByText("Échec de l'aperçu")).toBeInTheDocument()
  })
})
