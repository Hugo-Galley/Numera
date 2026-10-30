/** Provisions (page Épargne) : chargement, création, modification, pause, suppression, erreurs. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import type { Provision } from "./ProvisionCard"
import { ProvisionsSection } from "./ProvisionsSection"

type Body = Record<string, unknown>

const provision = (overrides: Partial<Provision> = {}): Provision => ({
  id: 3,
  name: "Taxe foncière",
  amount: 1200,
  interval_months: 12,
  due_date: "2026-10-15",
  category_id: null,
  account_id: null,
  note: null,
  active: true,
  category_name: null,
  account_name: null,
  next_due: "2026-10-15",
  previous_due: "2025-10-15",
  months_left: 4,
  monthly_amount: 100,
  target_now: 800,
  monthly_needed: 100,
  funded: null,
  status: "untracked",
  last_payment: null,
  ...overrides,
})

function setup(list: Provision[] = [], onPost: (body: Body) => Response | Promise<Response> = () => HttpResponse.json({ id: 1 })) {
  const posted: Body[] = []
  let loads = 0
  server.use(
    http.get(apiUrl("/provisions"), () => {
      loads++
      return HttpResponse.json(list)
    }),
    http.get(apiUrl("/provisions/summary"), () => HttpResponse.json({ monthly_total: 0, target_now_total: 0, behind_count: 0, accounts: [] })),
    http.get(apiUrl("/categories"), () =>
      HttpResponse.json([
        { id: 5, name: "Impôts", type: "depense" },
        { id: 6, name: "Salaire", type: "revenu" },
      ]),
    ),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([{ id: 2, name: "Livret A", type: "epargne" }])),
    http.post(apiUrl("/provisions"), async ({ request }) => {
      const body = (await request.json()) as Body
      posted.push(body)
      return onPost(body)
    }),
  )
  const view = renderWithProviders(<ProvisionsSection />, { auth: true })
  return { ...view, posted, loads: () => loads }
}

async function openCreate(user: ReturnType<typeof setup>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Nouvelle provision" }))
  return screen.getByRole("dialog", { name: "Nouvelle provision" })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date("2026-06-15T10:00:00"))
})
afterEach(() => vi.useRealTimers())

describe("ProvisionsSection", () => {
  it("affiche une erreur avec « Réessayer » si la liste ne charge pas", async () => {
    setup()
    server.use(http.get(apiUrl("/provisions"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))

    expect(await screen.findByText("Les provisions n'ont pas pu être chargées.")).toBeInTheDocument()
    expect(screen.queryByText(/Déclarez vos grosses dépenses/)).not.toBeInTheDocument()
  })

  it("refuse un montant négatif sans rien envoyer", async () => {
    const { user, posted } = setup()
    const dialog = await openCreate(user)

    expect(within(dialog).getByLabelText("Prochaine échéance")).toHaveValue("2026-06-15")
    await user.type(within(dialog).getByLabelText("Nom"), "Assurance")
    await user.type(within(dialog).getByLabelText("Montant par échéance (€)"), "-300")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Nom, montant et date d'échéance sont requis")).toBeInTheDocument()
    expect(posted).toHaveLength(0)
  })

  it("crée la provision : virgule décimale, périodicité, catégorie de dépense, compte suivi", async () => {
    const { user, posted, loads } = setup()
    const dialog = await openCreate(user)
    await waitFor(() => expect(loads()).toBe(1))

    await user.type(within(dialog).getByLabelText("Nom"), " Assurance auto ")
    await user.type(within(dialog).getByLabelText("Montant par échéance (€)"), "612,30")
    const [interval, category, account] = within(dialog).getAllByRole("combobox")
    await user.click(interval)
    await user.click(await screen.findByRole("option", { name: "Semestrielle" }))
    await user.click(category)
    expect(screen.queryByRole("option", { name: "Salaire" })).not.toBeInTheDocument()
    await user.click(await screen.findByRole("option", { name: "Impôts" }))
    await user.click(account)
    await user.click(await screen.findByRole("option", { name: "Livret A" }))
    await user.clear(within(dialog).getByLabelText("Prochaine échéance"))
    await user.type(within(dialog).getByLabelText("Prochaine échéance"), "2026-09-01")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Provision créée")).toBeInTheDocument()
    expect(posted).toEqual([
      { name: "Assurance auto", amount: 612.3, interval_months: 6, due_date: "2026-09-01", category_id: 5, account_id: 2, note: null },
    ])
    await waitFor(() => expect(loads()).toBe(2))
  })

  it("désactive « Enregistrer » pendant l'envoi", async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    const { user, posted } = setup([], async () => {
      await gate
      return HttpResponse.json({ id: 1 })
    })
    const dialog = await openCreate(user)

    await user.type(within(dialog).getByLabelText("Nom"), "Assurance")
    await user.type(within(dialog).getByLabelText("Montant par échéance (€)"), "300")
    const save = within(dialog).getByRole("button", { name: "Enregistrer" })
    await user.click(save)

    await waitFor(() => expect(save).toBeDisabled())
    await user.click(save)
    release()
    await screen.findByText("Provision créée")
    expect(posted).toHaveLength(1)
  })

  it("affiche le détail de l'erreur serveur", async () => {
    const { user } = setup([], () => HttpResponse.json({ detail: "Compte archivé" }, { status: 400 }))
    const dialog = await openCreate(user)

    await user.type(within(dialog).getByLabelText("Nom"), "Assurance")
    await user.type(within(dialog).getByLabelText("Montant par échéance (€)"), "300")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Compte archivé")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Nouvelle provision" })).toBeInTheDocument()
  })

  it("modifie une provision (échéance = prochaine échéance calculée) et la met en pause", async () => {
    const patched: Body[] = []
    const { user } = setup([provision({ next_due: "2026-10-15", due_date: "2025-10-15" })])
    server.use(
      http.patch(apiUrl("/provisions/3"), async ({ request }) => {
        patched.push((await request.json()) as Body)
        return HttpResponse.json({})
      }),
    )

    await user.click(await screen.findByTitle("Modifier"))
    const dialog = screen.getByRole("dialog", { name: "Modifier la provision" })
    expect(within(dialog).getByLabelText("Prochaine échéance")).toHaveValue("2026-10-15")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))
    expect(await screen.findByText("Provision mise à jour")).toBeInTheDocument()
    expect(patched[0]).toMatchObject({ name: "Taxe foncière", amount: 1200, interval_months: 12, due_date: "2026-10-15" })

    await user.click(screen.getByRole("button", { name: "Mettre en pause" }))
    await waitFor(() => expect(patched[1]).toEqual({ active: false }))
  })

  it("ne supprime qu'après confirmation", async () => {
    const deleted: string[] = []
    const { user } = setup([provision()])
    server.use(
      http.delete(apiUrl("/provisions/3"), ({ request }) => {
        deleted.push(request.method)
        return HttpResponse.json({})
      }),
    )

    await user.click(await screen.findByTitle("Supprimer"))
    await user.click(await screen.findByRole("button", { name: "Annuler" }))
    expect(deleted).toHaveLength(0)

    await user.click(screen.getByTitle("Supprimer"))
    await user.click(await screen.findByRole("button", { name: "Supprimer" }))
    expect(await screen.findByText("Provision supprimée")).toBeInTheDocument()
    expect(deleted).toEqual(["DELETE"])
  })
})
