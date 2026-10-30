/** Objectifs d'épargne (page Épargne) : validation, création, modification, suppression, erreurs. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { GoalsGrid } from "./GoalsGrid"
import { GoalsHeader } from "./GoalsHeader"
import { useSavings } from "./useSavings"

type Body = Record<string, unknown>

/** Les objectifs seuls, branchés sur le vrai hook de la page (sans les graphiques). */
function GoalsOnly() {
  const ctx = useSavings()
  if (ctx.loading) return <p>Chargement</p>
  return (
    <>
      <GoalsHeader ctx={ctx} />
      <GoalsGrid ctx={ctx} />
    </>
  )
}

const goal = {
  id: 4,
  name: "Vacances Japon",
  target_amount: 5000,
  current_amount: 1200,
  percentage: 24,
  status: "on_track",
  monthly_required: 300,
  keyword: "japon",
  color: "#3b82f6",
  deadline: "2027-04-01",
  account_id: null,
  category_id: null,
}

function setup(goals: object[] = [], onPost: (body: Body) => Response | Promise<Response> = () => HttpResponse.json({ id: 9 })) {
  const posted: Body[] = []
  let goalLoads = 0
  server.use(
    http.get(apiUrl("/analytics/budget"), () => HttpResponse.json({})),
    http.get(apiUrl("/analytics/kpi-history"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/resilience"), () => HttpResponse.json({ months: null, liquid_savings: 0, avg_monthly_real_expenses: 0, months_used: 0 })),
    http.get(apiUrl("/goals"), () => {
      goalLoads++
      return HttpResponse.json(goals)
    }),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([{ id: 2, name: "Livret A", type: "epargne" }])),
    http.get(apiUrl("/categories"), () => HttpResponse.json([])),
    http.post(apiUrl("/goals"), async ({ request }) => {
      const body = (await request.json()) as Body
      posted.push(body)
      return onPost(body)
    }),
  )
  const view = renderWithProviders(<GoalsOnly />, { auth: true })
  return { ...view, posted, goalLoads: () => goalLoads }
}

async function openCreate(user: ReturnType<typeof setup>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Nouvel Objectif" }))
  return screen.getByRole("dialog", { name: "Créer un objectif" })
}

describe("Objectifs d'épargne", () => {
  it("exige un nom et un montant", async () => {
    const { user, posted } = setup()
    const dialog = await openCreate(user)

    await user.type(within(dialog).getByLabelText("Nom de l'objectif"), "Voiture")
    await user.click(within(dialog).getByRole("button", { name: "Créer l'objectif" }))

    expect(await screen.findByText("Veuillez remplir les champs obligatoires (Nom et Montant)")).toBeInTheDocument()
    expect(posted).toHaveLength(0)
  })

  it("crée l'objectif lié à un compte, avec couleur et date cible, puis recharge", async () => {
    const { user, posted, goalLoads } = setup()
    const dialog = await openCreate(user)
    await waitFor(() => expect(goalLoads()).toBe(1))

    await user.type(within(dialog).getByLabelText("Nom de l'objectif"), "Voiture")
    await user.type(within(dialog).getByLabelText("Montant cible (€)"), "8000.50")
    await user.type(within(dialog).getByLabelText("Mot-clé Tag (optionnel)"), "auto")
    await user.type(within(dialog).getByLabelText("Date cible (optionnel)"), "2027-06-30")
    await user.click(within(dialog).getAllByRole("combobox")[0])
    await user.click(await screen.findByRole("option", { name: "Livret A" }))
    await user.click(within(dialog).getByRole("button", { name: "Couleur #8b5cf6" }))
    await user.click(within(dialog).getByRole("button", { name: "Créer l'objectif" }))

    expect(await screen.findByText("Objectif créé")).toBeInTheDocument()
    expect(posted).toEqual([
      {
        name: "Voiture",
        target_amount: 8000.5,
        keyword: "auto",
        color: "#8b5cf6",
        icon: "Target",
        deadline: "2027-06-30",
        account_id: 2,
        category_id: null,
      },
    ])
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    await waitFor(() => expect(goalLoads()).toBe(2))
  })

  it("désactive le bouton pendant l'envoi", async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    const { user, posted } = setup([], async () => {
      await gate
      return HttpResponse.json({ id: 9 })
    })
    const dialog = await openCreate(user)

    await user.type(within(dialog).getByLabelText("Nom de l'objectif"), "Voiture")
    await user.type(within(dialog).getByLabelText("Montant cible (€)"), "8000")
    const create = within(dialog).getByRole("button", { name: "Créer l'objectif" })
    await user.click(create)

    await waitFor(() => expect(create).toBeDisabled())
    await user.click(create)
    release()
    await screen.findByText("Objectif créé")
    expect(posted).toHaveLength(1)
  })

  it("garde le dialogue ouvert si le serveur refuse", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined)
    const { user } = setup([], () => HttpResponse.json({ detail: "Montant invalide" }, { status: 422 }))
    const dialog = await openCreate(user)

    await user.type(within(dialog).getByLabelText("Nom de l'objectif"), "Voiture")
    await user.type(within(dialog).getByLabelText("Montant cible (€)"), "8000")
    await user.click(within(dialog).getByRole("button", { name: "Créer l'objectif" }))

    expect(await screen.findByText("Une erreur est survenue lors de l'enregistrement")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Créer un objectif" })).toBeInTheDocument()
  })

  it("modifie un objectif par PATCH, formulaire prérempli", async () => {
    const patched: Body[] = []
    const { user } = setup([goal])
    server.use(
      http.patch(apiUrl("/goals/4"), async ({ request }) => {
        patched.push((await request.json()) as Body)
        return HttpResponse.json({})
      }),
    )

    await user.click(await screen.findByRole("button", { name: "Modifier l'objectif" }))
    const dialog = screen.getByRole("dialog", { name: "Modifier l'objectif" })
    expect(within(dialog).getByLabelText("Nom de l'objectif")).toHaveValue("Vacances Japon")
    const target = within(dialog).getByLabelText("Montant cible (€)")
    await user.clear(target)
    await user.type(target, "6000")
    await user.click(within(dialog).getByRole("button", { name: "Mettre à jour" }))

    expect(await screen.findByText("Objectif mis à jour")).toBeInTheDocument()
    expect(patched[0]).toMatchObject({ name: "Vacances Japon", target_amount: 6000, keyword: "japon", deadline: "2027-04-01" })
  })

  it("ne supprime qu'après confirmation", async () => {
    const deleted: string[] = []
    const { user } = setup([goal])
    server.use(
      http.delete(apiUrl("/goals/4"), ({ request }) => {
        deleted.push(request.method)
        return HttpResponse.json({})
      }),
    )

    await user.click(await screen.findByRole("button", { name: "Supprimer l'objectif" }))
    await user.click(await screen.findByRole("button", { name: "Annuler" }))
    expect(deleted).toHaveLength(0)

    await user.click(screen.getByRole("button", { name: "Supprimer l'objectif" }))
    await user.click(await screen.findByRole("button", { name: "Supprimer" }))
    expect(await screen.findByText("Objectif supprimé")).toBeInTheDocument()
    expect(deleted).toEqual(["DELETE"])
  })

  // Bug suspect (pages/Savings/useSavingsData.ts, handleCreateOrUpdateGoal) : un 422 { detail: "Montant invalide" }
  // affiche seulement « Une erreur est survenue lors de l'enregistrement » ; attendu : errorMessage(error, …).
  it.todo("affiche le détail renvoyé par le serveur quand l'objectif est refusé")
})
