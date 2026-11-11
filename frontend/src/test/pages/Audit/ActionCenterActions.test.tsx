/** Centre d'Actions : liste, masquage, navigation, fenêtres de création, détail d'un problème et ses actions. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeAccount, makeActionCenter, makeCategory, makeTransaction } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { LocationDisplay } from "@/test/support/LocationDisplay"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import ActionCenter from "@/pages/Audit/index"
import type { ActionItem } from "@/pages/Audit/types"

function makeAction(overrides: Partial<ActionItem> = {}): ActionItem {
  return {
    id: "a1",
    type: "audit",
    severity: "high",
    title: "Transactions sans catégorie",
    description: "3 transactions n'ont pas de catégorie",
    action_label: "Catégoriser",
    action_type: "modal_categorize",
    metadata: { issue_id: "uncategorized" },
    samples: [],
    ...overrides,
  }
}

function serveCenter(actions: ActionItem[]) {
  const state = { actions, centerLoads: 0, writes: [] as { method: string; path: string; body: unknown }[] }
  const record = async (request: Request, path: string) => {
    const text = await request.text()
    state.writes.push({ method: request.method, path, body: text ? JSON.parse(text) : null })
  }
  server.use(
    http.get(apiUrl("/analytics/actions"), () => {
      state.centerLoads += 1
      return HttpResponse.json(makeActionCenter({ actions: state.actions, summary: { total_actions: state.actions.length, high_priority: 1, medium_priority: 2, low_priority: 3, checked_at: "2026-06-15T10:00:00" } }))
    }),
    http.get(apiUrl("/categories"), () => HttpResponse.json([makeCategory({ id: 3, name: "Courses" })])),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([makeAccount({ id: 1, name: "Compte courant" })])),
    http.post(apiUrl("/analytics/actions/dismiss"), async ({ request }) => {
      await record(request, "/analytics/actions/dismiss")
      return HttpResponse.json({})
    }),
    http.post(apiUrl("/transactions/:id/ignore-duplicate"), async ({ request, params }) => {
      await record(request, `/transactions/${params.id}/ignore-duplicate`)
      return new HttpResponse(null, { status: 204 })
    }),
    http.post(apiUrl("/transactions/:id/ignore"), async ({ request, params }) => {
      await record(request, `/transactions/${params.id}/ignore`)
      return new HttpResponse(null, { status: 204 })
    }),
    http.post(apiUrl("/transactions/:id/link/:other"), async ({ request, params }) => {
      await record(request, `/transactions/${params.id}/link/${params.other}${new URL(request.url).search}`)
      return HttpResponse.json({})
    }),
  )
  return state
}

const page = () => renderWithProviders(<><ActionCenter /><LocationDisplay /></>, { route: "/audit", auth: true })

describe("Centre d'Actions : liste", () => {
  it("affiche les compteurs, chaque action avec sa sévérité, son libellé et un exemple", async () => {
    serveCenter([makeAction({ samples: [{ merchant: "Carrefour" }] }), makeAction({ id: "a2", severity: "low", title: "Abonnement inutilisé", action_label: null, action_type: "link", action_url: "/subscriptions" })])
    page()

    expect(await screen.findByText("Transactions sans catégorie")).toBeInTheDocument()
    expect(screen.getByText("Abonnement inutilisé")).toBeInTheDocument()
    expect(screen.getByText("Ex: Carrefour")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Catégoriser/ })).toBeInTheDocument()
    // Libellé par défaut quand l'action n'en fournit pas
    expect(screen.getByRole("button", { name: /Traiter/ })).toBeInTheDocument()
    expect(screen.getAllByText("Priorité haute").length).toBeGreaterThan(1)
  })

  it("aucune action : message « Tout est à jour »", async () => {
    serveCenter([])
    page()

    expect(await screen.findByText("Tout est à jour")).toBeInTheDocument()
  })

  it("analyse en échec : message d'erreur, « Relancer l'analyse » refait la requête", async () => {
    let fail = true
    server.use(
      http.get(apiUrl("/analytics/actions"), () => (fail ? HttpResponse.json({ detail: "Base verrouillée" }, { status: 500 }) : HttpResponse.json(makeActionCenter()))),
      http.get(apiUrl("/categories"), () => HttpResponse.json([])),
      http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
    )
    const { user } = page()

    expect(await screen.findByText("Centre d'actions indisponible")).toBeInTheDocument()
    expect(screen.getByText("Base verrouillée")).toBeInTheDocument()
    fail = false
    await user.click(screen.getByRole("button", { name: "Relancer l'analyse" }))

    expect(await screen.findByText("Tout est à jour")).toBeInTheDocument()
  })

  it("masquer une action : POST avec son identifiant, la ligne disparaît, sans ouvrir son détail", async () => {
    const state = serveCenter([makeAction(), makeAction({ id: "a2", title: "Budget dépassé", action_type: "link", action_url: "/budgets" })])
    const { user } = page()
    await screen.findByText("Transactions sans catégorie")

    await user.click(screen.getAllByTitle("Masquer cette action définitivement")[0])

    await waitFor(() => expect(screen.queryByText("Transactions sans catégorie")).not.toBeInTheDocument())
    expect(state.writes).toEqual([{ method: "POST", path: "/analytics/actions/dismiss", body: { id: "a1" } }])
    expect(screen.getByText("Budget dépassé")).toBeInTheDocument()
    expect(await screen.findByText("Action masquée")).toBeInTheDocument()
  })

  it("masquage refusé par le serveur : message d'erreur, l'action reste", async () => {
    serveCenter([makeAction()])
    server.use(http.post(apiUrl("/analytics/actions/dismiss"), () => HttpResponse.json({ detail: "non" }, { status: 500 })))
    const { user } = page()
    await screen.findByText("Transactions sans catégorie")

    await user.click(screen.getByTitle("Masquer cette action définitivement"))

    expect(await screen.findByText("Impossible de masquer l'action")).toBeInTheDocument()
    expect(screen.getByText("Transactions sans catégorie")).toBeInTheDocument()
  })

  it("action de type lien : navigue vers son adresse", async () => {
    serveCenter([makeAction({ type: "budget", title: "Budget dépassé", action_label: "Voir", action_type: "link", action_url: "/budgets?month=2026-06", metadata: {} })])
    const { user } = page()

    await user.click(await screen.findByText("Budget dépassé"))

    expect(await screen.findByLabelText("adresse")).toHaveTextContent("/budgets?month=2026-06")
  })

  it("« Virements internes » ouvre la revue des virements", async () => {
    serveCenter([])
    server.use(
      http.get(apiUrl("/transactions/potential-transfers"), () => HttpResponse.json([])),
      http.get(apiUrl("/transactions"), () => HttpResponse.json([])),
    )
    const { user } = page()

    await user.click(await screen.findByRole("button", { name: "Virements internes" }))

    expect(await screen.findByLabelText("adresse")).toHaveTextContent("/audit?vue=virements")
    expect(await screen.findByRole("button", { name: /Retour au centre d'actions/ })).toBeInTheDocument()
  })
})

describe("Centre d'Actions : fenêtres de création", () => {
  it("action « règle » : ouvre la fenêtre avec le marchand et la catégorie suggérée", async () => {
    serveCenter([makeAction({ id: "r1", type: "rule", title: "Règle suggérée", action_label: "Créer", action_type: "modal_rule", metadata: { merchant: "NETFLIX", suggested_category_id: 3 } })])
    const { user } = page()

    await user.click(await screen.findByText("Règle suggérée"))

    const dialog = await screen.findByRole("dialog")
    expect(dialog).toHaveTextContent("Créer une règle d'auto-catégorisation")
    expect(within(dialog).getByDisplayValue("NETFLIX")).toBeInTheDocument()
  })

  it("règle créée : la fenêtre se ferme et l'analyse est relancée", async () => {
    const state = serveCenter([makeAction({ id: "r1", type: "rule", title: "Règle suggérée", action_type: "modal_rule", metadata: { merchant: "NETFLIX" } })])
    server.use(http.post(apiUrl("/categorization-rules/"), () => HttpResponse.json({ id: 1 })))
    const { user } = page()
    await user.click(await screen.findByText("Règle suggérée"))
    const before = state.centerLoads

    await user.click(await screen.findByRole("button", { name: "Créer la règle" }))

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    expect(state.centerLoads).toBeGreaterThan(before)
  })

  it("action « marchand » : ouvre la fenêtre de normalisation", async () => {
    serveCenter([makeAction({ id: "m1", title: "Marchands à normaliser", action_type: "modal_merchant", metadata: { merchant: "CB CARREFOUR 12", variants: ["CB CARREFOUR 12", "CARREFOUR MKT"] } })])
    const { user } = page()

    await user.click(await screen.findByText("Marchands à normaliser"))

    const dialog = await screen.findByRole("dialog")
    expect(dialog).toHaveTextContent("Normaliser le marchand")
    expect(within(dialog).getByDisplayValue("CB CARREFOUR 12")).toBeInTheDocument()
  })
})

describe("Centre d'Actions : détail d'un problème", () => {
  const serveIssue = (body: unknown, status = 200) =>
    server.use(http.get(apiUrl("/analytics/audit/uncategorized"), () => HttpResponse.json(body as object, { status })))

  it("charge le détail et affiche chaque transaction éditable ; « Retour » revient à la liste", async () => {
    serveCenter([makeAction()])
    serveIssue({ issue_id: "uncategorized", transactions: [makeTransaction({ id: 21, merchant: "Boulangerie", account_id: 1 })] })
    const { user } = page()

    await user.click(await screen.findByText("Transactions sans catégorie"))

    expect(await screen.findAllByDisplayValue("Boulangerie")).not.toHaveLength(0)
    await user.click(screen.getByRole("button", { name: /Retour au centre d'actions/ }))
    expect(await screen.findByRole("button", { name: "Actualiser" })).toBeInTheDocument()
  })

  it("détail déjà chargé : rouvrir l'action ne refait pas la requête", async () => {
    serveCenter([makeAction()])
    let loads = 0
    server.use(http.get(apiUrl("/analytics/audit/uncategorized"), () => { loads += 1; return HttpResponse.json({ issue_id: "uncategorized", transactions: [makeTransaction({ id: 21, merchant: "Boulangerie" })] }) }))
    const { user } = page()

    await user.click(await screen.findByText("Transactions sans catégorie"))
    await screen.findAllByDisplayValue("Boulangerie")
    await user.click(screen.getByRole("button", { name: /Retour au centre d'actions/ }))
    await user.click(await screen.findByText("Transactions sans catégorie"))

    await screen.findAllByDisplayValue("Boulangerie")
    expect(loads).toBe(1)
  })

  it("détail vide : « Tout est corrigé ! » et retour à la liste", async () => {
    serveCenter([makeAction()])
    serveIssue({ issue_id: "uncategorized", transactions: [] })
    const { user } = page()

    await user.click(await screen.findByText("Transactions sans catégorie"))

    expect(await screen.findByText("Tout est corrigé !")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Retourner à la liste" }))
    expect(await screen.findByRole("button", { name: "Actualiser" })).toBeInTheDocument()
  })

  it("chargement du détail en échec : message d'erreur", async () => {
    serveCenter([makeAction()])
    serveIssue({ detail: "Audit indisponible" }, 500)
    const { user } = page()

    await user.click(await screen.findByText("Transactions sans catégorie"))

    expect(await screen.findByText("Audit indisponible")).toBeInTheDocument()
  })

  it("doublons : « Marquer comme OK » ignore chaque transaction du groupe puis recharge", async () => {
    const state = serveCenter([makeAction({ id: "d1", title: "Doublons", action_type: "modal_categorize", metadata: { issue_id: "uncategorized" } })])
    serveIssue({
      issue_id: "uncategorized",
      duplicate_groups: [{ key: "g1", count: 2, transactions: [makeTransaction({ id: 31, merchant: "Spotify" }), makeTransaction({ id: 32, merchant: "Spotify" })] }],
    })
    const { user } = page()
    await user.click(await screen.findByText("Doublons"))
    expect(await screen.findByText("2 transactions identiques détectées")).toBeInTheDocument()
    const before = state.centerLoads

    await user.click(screen.getByRole("button", { name: "Marquer comme OK" }))

    await waitFor(() => expect(state.writes.map((w) => w.path).sort()).toEqual(["/transactions/31/ignore-duplicate", "/transactions/32/ignore-duplicate"]))
    expect(await screen.findByText("Doublons ignorés")).toBeInTheDocument()
    await waitFor(() => expect(state.centerLoads).toBeGreaterThan(before))
  })

  it("virements : « Rapprocher » lie la sortie et l'entrée, « Ignorer » écarte la suggestion", async () => {
    const state = serveCenter([makeAction({ id: "t1", title: "Virements à rapprocher", action_type: "modal_categorize", metadata: { issue_id: "uncategorized" } })])
    serveIssue({
      issue_id: "uncategorized",
      transfer_pairs: [{ sortie: makeTransaction({ id: 41, type: "Sortie", amount: 200 }), entree: makeTransaction({ id: 42, type: "Entree", amount: 200, account_id: 2 }) }],
    })
    const { user } = page()
    await user.click(await screen.findByText("Virements à rapprocher"))

    await user.click(await screen.findByRole("button", { name: "Rapprocher" }))
    await waitFor(() => expect(state.writes).toContainEqual({ method: "POST", path: "/transactions/41/link/42?type=regular", body: {} }))
    expect(await screen.findByText("Transfert rapproché")).toBeInTheDocument()

    await user.click(await screen.findByRole("button", { name: "Ignorer" }))
    await waitFor(() => expect(state.writes).toContainEqual({ method: "POST", path: "/transactions/41/ignore", body: {} }))
    expect(await screen.findByText("Suggestion ignorée")).toBeInTheDocument()
  })

  it("rapprochement refusé : message d'erreur du serveur", async () => {
    serveCenter([makeAction({ id: "t1", title: "Virements à rapprocher", metadata: { issue_id: "uncategorized" } })])
    serveIssue({
      issue_id: "uncategorized",
      transfer_pairs: [{ sortie: makeTransaction({ id: 41, amount: 200 }), entree: makeTransaction({ id: 42, type: "Entree", amount: 200 }) }],
    })
    server.use(http.post(apiUrl("/transactions/:id/link/:other"), () => HttpResponse.json({ detail: "Déjà lié" }, { status: 409 })))
    const { user } = page()
    await user.click(await screen.findByText("Virements à rapprocher"))

    await user.click(await screen.findByRole("button", { name: "Rapprocher" }))

    expect(await screen.findByText("Déjà lié")).toBeInTheDocument()
  })
})
