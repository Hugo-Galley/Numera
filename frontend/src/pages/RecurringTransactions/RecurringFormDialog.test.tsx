/** Formulaire de récurrence (Échéances) : validation, fréquences, mois exclus, envoi et erreurs. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { safeStorage } from "@/lib/storage"
import { apiUrl } from "@/test/handlers"
import { makeAccount } from "@/test/factories"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import RecurringTransactions from "."

type Body = Record<string, unknown>

const account = makeAccount({ id: 3, name: "Courant", type: "courant" })

/** Charge la page en vue « Liste » ; `onPost` répond au `POST /recurring-transactions/`. */
function setup(onPost: (body: Body) => Response | Promise<Response> = () => HttpResponse.json({ id: 1 })) {
  const posted: Body[] = []
  server.use(
    http.get(apiUrl("/recurring-transactions/"), () => HttpResponse.json([])),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([account])),
    http.get(apiUrl("/categories"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/subscriptions"), () => HttpResponse.json({ subscriptions: [] })),
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    http.post(apiUrl("/recurring-transactions/"), async ({ request }) => {
      const body = (await request.json()) as Body
      posted.push(body)
      return onPost(body)
    }),
  )
  safeStorage.setItem("recurring-view", "list")
  const view = renderWithProviders(<RecurringTransactions />, { auth: true })
  return { ...view, posted }
}

async function openForm(user: ReturnType<typeof setup>["user"]) {
  await waitFor(() => expect(screen.getAllByText("0 récurrence(s) configurée(s) au total.").length).toBeGreaterThan(0))
  await user.click(screen.getByRole("button", { name: "Nouvelle récurrence" }))
  return screen.getByRole("dialog", { name: "Nouvelle récurrence" })
}

async function pick(user: ReturnType<typeof setup>["user"], label: string, option: string) {
  await user.click(screen.getByRole("combobox", { name: label }))
  await user.click(await screen.findByRole("option", { name: option }))
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date("2026-06-15T10:00:00"))
})
afterEach(() => vi.useRealTimers())

describe("Formulaire de récurrence", () => {
  it("refuse un nom vide sans rien envoyer", async () => {
    const { user, posted } = setup()
    const dialog = await openForm(user)

    await user.type(within(dialog).getByLabelText("Montant"), "15")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Veuillez remplir les champs obligatoires")).toBeInTheDocument()
    expect(posted).toHaveLength(0)
    expect(dialog).toBeInTheDocument()
  })

  it("crée une récurrence trimestrielle : montant positif, date naïve, pas de mois exclus", async () => {
    const { user, posted } = setup()
    const dialog = await openForm(user)

    await user.type(within(dialog).getByLabelText("Nom / Marchand"), "Assurance habitation")
    await user.type(within(dialog).getByLabelText("Montant"), "42.5")
    await pick(user, "Fréquence", "Trimestrielle")
    await user.clear(within(dialog).getByLabelText("Jour du mois"))
    await user.type(within(dialog).getByLabelText("Jour du mois"), "12")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Transaction récurrente créée")).toBeInTheDocument()
    expect(posted).toHaveLength(1)
    expect(posted[0]).toMatchObject({
      name: "Assurance habitation",
      account_id: 3,
      type: "Sortie",
      amount: 42.5,
      frequency: "quarterly",
      day_of_month: 12,
      excluded_months: null,
      start_date: "2026-06-15T00:00:00",
      transfer_to_account_id: null,
      category_id: null,
      ticker: null,
    })
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
  })

  it("envoie les mois exclus d'une récurrence mensuelle", async () => {
    const { user, posted } = setup()
    const dialog = await openForm(user)

    await user.type(within(dialog).getByLabelText("Nom / Marchand"), "Cantine")
    await user.type(within(dialog).getByLabelText("Montant"), "80")
    await user.click(within(dialog).getByRole("button", { name: /Mois irréguliers/ }))
    await user.click(within(dialog).getByRole("button", { name: "Août" }))
    await user.click(within(dialog).getByRole("button", { name: "Juil" }))
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    await screen.findByText("Transaction récurrente créée")
    expect(posted[0]).toMatchObject({ frequency: "monthly", excluded_months: [7, 8] })
  })

  it("abandonne les mois exclus quand la fréquence n'est plus mensuelle", async () => {
    const { user, posted } = setup()
    const dialog = await openForm(user)

    await user.type(within(dialog).getByLabelText("Nom / Marchand"), "Taxe foncière")
    await user.type(within(dialog).getByLabelText("Montant"), "900")
    await user.click(within(dialog).getByRole("button", { name: /Mois irréguliers/ }))
    await user.click(within(dialog).getByRole("button", { name: "Mai" }))
    await pick(user, "Fréquence", "Annuelle")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    await screen.findByText("Transaction récurrente créée")
    expect(posted[0]).toMatchObject({ frequency: "yearly", excluded_months: null })
  })

  it("désactive le bouton pendant l'envoi et n'envoie qu'une requête", async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    const { user, posted } = setup(async () => {
      await gate
      return HttpResponse.json({ id: 1 })
    })
    const dialog = await openForm(user)

    await user.type(within(dialog).getByLabelText("Nom / Marchand"), "Loyer")
    await user.type(within(dialog).getByLabelText("Montant"), "700")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    const busy = await within(dialog).findByRole("button", { name: "Enregistrement…" })
    expect(busy).toBeDisabled()
    await user.click(busy)
    release()
    await screen.findByText("Transaction récurrente créée")
    expect(posted).toHaveLength(1)
  })

  it("garde le formulaire ouvert et affiche un toast si le serveur refuse", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined)
    const { user } = setup(() => HttpResponse.json({ detail: "Compte inconnu" }, { status: 400 }))
    const dialog = await openForm(user)

    await user.type(within(dialog).getByLabelText("Nom / Marchand"), "Loyer")
    await user.type(within(dialog).getByLabelText("Montant"), "700")
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Erreur lors de l'enregistrement")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Nouvelle récurrence" })).toBeInTheDocument()
  })

  // Bug suspect (useRecurringActions.ts, handleSubmit) : un 400 { detail: "Compte inconnu" } affiche seulement
  // « Erreur lors de l'enregistrement » ; attendu : errorMessage(error, …) pour montrer le détail du serveur.
  it.todo("affiche le détail renvoyé par le serveur quand l'enregistrement est refusé")
})
