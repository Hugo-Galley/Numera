/** Aides perçues : chargement, création (préréglages, validation, envoi), erreurs, suppression avec confirmation. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { BenefitsSection, type Benefit } from "./BenefitsSection"

type Body = Record<string, unknown>

const benefit = (overrides: Partial<Benefit> = {}): Benefit => ({
  id: 7,
  name: "APL",
  organization: "CAF",
  amount: 250,
  payment_day: 5,
  match_pattern: "CAF",
  account_id: null,
  start_date: null,
  declaration_interval_months: null,
  next_declaration_date: null,
  note: null,
  active: true,
  account_name: null,
  status: "received",
  expected_date: "2026-06-05",
  next_payment_date: "2026-07-05",
  last_payment: null,
  amount_changed: false,
  received_this_year: 1500,
  payments: [],
  declaration_days_left: null,
  ...overrides,
})

const summary = { monthly_expected_total: 0, received_this_year: 0, received_last_12_months: 0, late_count: 0 }

function setup(list: Benefit[] = [], onPost: (body: Body) => Response | Promise<Response> = () => HttpResponse.json({ id: 1 })) {
  const posted: Body[] = []
  let loads = 0
  server.use(
    http.get(apiUrl("/benefits"), () => {
      loads++
      return HttpResponse.json(list)
    }),
    http.get(apiUrl("/benefits/summary"), () => HttpResponse.json(summary)),
    http.get(apiUrl("/accounts"), () =>
      HttpResponse.json([
        { id: 1, name: "Courant", type: "courant" },
        { id: 2, name: "PEA", type: "investissement" },
      ]),
    ),
    http.post(apiUrl("/benefits"), async ({ request }) => {
      const body = (await request.json()) as Body
      posted.push(body)
      return onPost(body)
    }),
  )
  const view = renderWithProviders(<BenefitsSection />, { auth: true })
  return { ...view, posted, loads: () => loads }
}

async function openCreate(user: ReturnType<typeof setup>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Nouvelle aide" }))
  return screen.getByRole("dialog", { name: "Nouvelle aide" })
}

describe("BenefitsSection", () => {
  it("affiche une erreur avec « Réessayer » si la liste ne charge pas, pas un état vide", async () => {
    setup()
    server.use(http.get(apiUrl("/benefits"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))

    expect(await screen.findByText("Les aides n'ont pas pu être chargées.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument()
    expect(screen.queryByText(/Déclarez vos aides/)).not.toBeInTheDocument()
  })

  it("refuse un montant nul ou un libellé trop court sans rien envoyer", async () => {
    const { user, posted } = setup()
    const dialog = await openCreate(user)

    await user.type(within(dialog).getByLabelText("Nom"), "Prime")
    await user.type(within(dialog).getByLabelText("Organisme"), "CAF")
    await user.type(within(dialog).getByLabelText("Montant mensuel (€)"), "0")
    await user.type(within(dialog).getByLabelText("Texte du libellé bancaire"), "C")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Nom, organisme, montant et texte du libellé sont requis")).toBeInTheDocument()
    expect(posted).toHaveLength(0)
  })

  it("exige la date de la prochaine déclaration quand le préréglage en impose une", async () => {
    const { user, posted } = setup()
    const dialog = await openCreate(user)

    await user.click(within(dialog).getByRole("button", { name: "Prime d'activité" }))
    expect(within(dialog).getByLabelText("Nom")).toHaveValue("Prime d'activité")
    expect(within(dialog).getByLabelText("Organisme")).toHaveValue("CAF")
    await user.type(within(dialog).getByLabelText("Montant mensuel (€)"), "180")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Indiquez la date de la prochaine déclaration")).toBeInTheDocument()
    expect(posted).toHaveLength(0)
  })

  it("crée l'aide : montant décimal à virgule, jour borné, déclaration trimestrielle, puis recharge", async () => {
    const { user, posted, loads } = setup()
    const dialog = await openCreate(user)
    await waitFor(() => expect(loads()).toBe(1))

    await user.click(within(dialog).getByRole("button", { name: "Prime d'activité" }))
    await user.type(within(dialog).getByLabelText("Montant mensuel (€)"), "182,40")
    await user.clear(within(dialog).getByLabelText("Jour de versement"))
    await user.type(within(dialog).getByLabelText("Jour de versement"), "45")
    await user.type(within(dialog).getByLabelText("Prochaine déclaration"), "2026-07-01")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Aide ajoutée")).toBeInTheDocument()
    expect(posted).toEqual([
      {
        name: "Prime d'activité",
        organization: "CAF",
        amount: 182.4,
        payment_day: 31,
        match_pattern: "CAF",
        account_id: null,
        start_date: null,
        declaration_interval_months: 3,
        next_declaration_date: "2026-07-01",
        note: null,
      },
    ])
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
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

    await user.click(within(dialog).getByRole("button", { name: "APL" }))
    await user.type(within(dialog).getByLabelText("Montant mensuel (€)"), "250")
    const save = within(dialog).getByRole("button", { name: "Enregistrer" })
    await user.click(save)

    await waitFor(() => expect(save).toBeDisabled())
    await user.click(save)
    release()
    await screen.findByText("Aide ajoutée")
    expect(posted).toHaveLength(1)
  })

  it("affiche le détail de l'erreur serveur et garde le dialogue ouvert", async () => {
    const { user } = setup([], () => HttpResponse.json({ detail: "Organisme inconnu" }, { status: 400 }))
    const dialog = await openCreate(user)

    await user.click(within(dialog).getByRole("button", { name: "APL" }))
    await user.type(within(dialog).getByLabelText("Montant mensuel (€)"), "250")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Organisme inconnu")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Nouvelle aide" })).toBeInTheDocument()
  })

  it("modifie une aide existante par PATCH", async () => {
    const patched: Body[] = []
    const { user } = setup([benefit()])
    server.use(
      http.patch(apiUrl("/benefits/7"), async ({ request }) => {
        patched.push((await request.json()) as Body)
        return HttpResponse.json({})
      }),
    )

    await user.click(await screen.findByTitle("Modifier"))
    const dialog = screen.getByRole("dialog", { name: "Modifier l'aide" })
    const amount = within(dialog).getByLabelText("Montant mensuel (€)")
    expect(amount).toHaveValue("250")
    await user.clear(amount)
    await user.type(amount, "260")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Aide mise à jour")).toBeInTheDocument()
    expect(patched[0]).toMatchObject({ name: "APL", amount: 260, payment_day: 5 })
  })

  it("ne supprime qu'après confirmation", async () => {
    const deleted: string[] = []
    const { user } = setup([benefit()])
    server.use(
      http.delete(apiUrl("/benefits/7"), ({ request }) => {
        deleted.push(request.url)
        return HttpResponse.json({})
      }),
    )

    await user.click(await screen.findByTitle("Supprimer"))
    await user.click(await screen.findByRole("button", { name: "Annuler" }))
    expect(deleted).toHaveLength(0)

    await user.click(screen.getByTitle("Supprimer"))
    await user.click(await screen.findByRole("button", { name: "Supprimer" }))
    expect(await screen.findByText("Aide supprimée")).toBeInTheDocument()
    expect(deleted).toHaveLength(1)
  })
})
