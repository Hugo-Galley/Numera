/** Revue de fin de mois : validation des soldes des comptes et catégorisation des dépenses restantes. */
import { screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { makeCategory } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { confirmUnchangedAccounts } from "@/test/support/handlers/monthReview"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { recordRequests } from "@/test/support/recordRequests"
import { AccountsStep } from "@/components/month-review/AccountsStep"
import { CategorizeStep } from "@/components/month-review/CategorizeStep"
import type { MonthReview } from "@/types/monthReview"

const account = (overrides: Partial<MonthReview["accounts"]["accounts"][number]> = {}): MonthReview["accounts"]["accounts"][number] => ({
  id: 1, name: "Compte courant", currency: "EUR", balance: 1234.5, last_verified_at: "2025-09-28T10:00:00", verified_since_month_end: false,
  group: "reconcile", statement_date: "2025-10-31", statement_balance: 1248.3, ...overrides,
})
const tx = (id: number, merchant: string, amount: number) => ({ id, date: "2026-06-12T10:00:00", merchant, amount, category_name: null, is_exceptional: false })

describe("AccountsStep", () => {
  const step = (accounts: ReturnType<typeof account>[]) => ({ unverified_count: accounts.filter((a) => !a.verified_since_month_end).length, accounts })
  const reconcileResult = (overrides: object = {}) => ({
    account_id: 1, date: "2025-10-31", currency: "EUR", bank_balance: 1248.3, numera_balance: 1248.3, gap: 0, matches: true, verified: true, hints: [], ...overrides,
  })
  const renderStep = (accounts: ReturnType<typeof account>[], props: { onChanged?: () => void; onReview?: (data: MonthReview) => void } = {}) =>
    renderWithProviders(
      <AccountsStep step={step(accounts)} year={2025} month={10} onChanged={props.onChanged ?? vi.fn()} onReview={props.onReview ?? vi.fn()} />,
      { auth: true },
    )

  it("rapproche un compte au solde du relevé et valide s'il colle", async () => {
    const bodies: unknown[] = []
    server.use(http.post(apiUrl("/accounts/:id/reconcile"), async ({ request, params }) => {
      bodies.push({ id: String(params.id), body: await request.json() })
      return HttpResponse.json(reconcileResult())
    }))
    const onChanged = vi.fn()
    const { user } = renderStep([account()], { onChanged })

    expect(screen.getByText("À rapprocher au 31/10/2025")).toBeInTheDocument()
    await user.type(screen.getByRole("textbox", { name: "Solde du relevé de Compte courant" }), "1 248,30{Enter}")

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1))
    expect(bodies).toEqual([{ id: "1", body: { date: "2025-10-31", bank_balance: 1248.3 } }])
    expect(await screen.findByText("Solde validé")).toBeInTheDocument()
  })

  it("un compte rapproché reste dans « À rapprocher » une fois la revue rechargée", async () => {
    server.use(http.post(apiUrl("/accounts/:id/reconcile"), () => HttpResponse.json(reconcileResult())))
    const props = { year: 2025, month: 10, onChanged: vi.fn(), onReview: vi.fn() }
    const { user, rerender } = renderWithProviders(<AccountsStep step={step([account()])} {...props} />, { auth: true })

    await user.type(screen.getByRole("textbox", { name: "Solde du relevé de Compte courant" }), "1248,30{Enter}")
    await waitFor(() => expect(props.onChanged).toHaveBeenCalledTimes(1))
    // Vérifié aujourd'hui, le compte n'a plus bougé depuis : le backend le range dans `unchanged`.
    rerender(<AccountsStep step={step([account({ group: "unchanged", verified_since_month_end: true })])} {...props} />)

    const block = screen.getByRole("region", { name: "À rapprocher au 31/10/2025" })
    expect(within(block).getByText("Compte courant")).toBeInTheDocument()
    expect(within(block).getByText("Validé")).toBeInTheDocument()
    expect(screen.queryByText(/Rien n'a bougé/)).not.toBeInTheDocument()
  })

  it("affiche l'écart et la cause probable", async () => {
    server.use(http.post(apiUrl("/accounts/:id/reconcile"), () => HttpResponse.json(reconcileResult({
      bank_balance: 1228.3, gap: -20, matches: false, verified: false,
      hints: [{ kind: "duplicate", message: "Doublon probable : Netflix", transactions: [{ id: 9, date: "2025-10-12", merchant: "Netflix", type: "Sortie", amount: 20 }] }],
    }))))
    const onChanged = vi.fn()
    const { user } = renderStep([account()], { onChanged })

    await user.type(screen.getByRole("textbox", { name: "Solde du relevé de Compte courant" }), "1228,30")
    await user.click(screen.getByRole("button", { name: "Vérifier" }))

    expect(await screen.findByText(/Écart de -20,00/)).toBeInTheDocument()
    expect(screen.getByText("Doublon probable : Netflix")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Ouvrir le compte" })).toHaveAttribute("href", "/accounts/1")
    expect(onChanged).not.toHaveBeenCalled()
  })

  it("« Valider sans saisir » valide le compte sans rapprochement", async () => {
    const posted: string[] = []
    server.use(http.post(apiUrl("/accounts/:id/verify"), ({ params }) => { posted.push(String(params.id)); return HttpResponse.json({}) }))
    const onChanged = vi.fn()
    const { user } = renderStep([account()], { onChanged })

    await user.click(screen.getByRole("button", { name: "Valider sans saisir" }))

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1))
    expect(posted).toEqual(["1"])
  })

  it("un compte déjà validé n'a plus de champ de relevé", () => {
    renderStep([account({ verified_since_month_end: true })])

    expect(screen.getByText("Validé")).toBeInTheDocument()
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument()
  })

  it("valide tous les comptes qui n'ont pas bougé", async () => {
    const requests = recordRequests()
    const bodies: unknown[] = []
    const review = { year: 2025, month: 10, accounts: { unverified_count: 0, accounts: [] } }
    server.use(confirmUnchangedAccounts(review, bodies))
    const onReview = vi.fn()
    const { user } = renderStep([
      account({ id: 2, name: "PEL", group: "unchanged" }),
      account({ id: 3, name: "Livret jeune", group: "unchanged" }),
    ], { onReview })

    expect(screen.getByText("Rien n'a bougé depuis la dernière vérification (2)")).toBeInTheDocument()
    expect(screen.getByText("PEL · Livret jeune")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Tout valider" }))

    await waitFor(() => expect(onReview).toHaveBeenCalledWith(review))
    expect(bodies).toEqual([{ year: 2025, month: 10 }])
    expect(requests.filter((r) => r.method !== "GET")).toEqual([])  // aucune autre écriture
    expect(await screen.findByText("Comptes validés")).toBeInTheDocument()
  })

  it("« Tout valider » disparaît quand les comptes inchangés sont déjà validés", () => {
    renderStep([account({ id: 2, name: "PEL", group: "unchanged", verified_since_month_end: true })])

    expect(screen.queryByRole("button", { name: "Tout valider" })).not.toBeInTheDocument()
  })

  it("garde les placements à part avec leur valeur actuelle", async () => {
    const posted: string[] = []
    server.use(http.post(apiUrl("/accounts/:id/verify"), ({ params }) => { posted.push(String(params.id)); return HttpResponse.json({}) }))
    const onChanged = vi.fn()
    const { user } = renderStep([account({ id: 4, name: "PEA", group: "market", balance: 12430, statement_balance: null })], { onChanged })

    const block = screen.getByRole("region", { name: "Placements (valeur actuelle)" })
    expect(within(block).getByText(/12\s430,00/)).toBeInTheDocument()
    expect(within(block).queryByRole("textbox")).not.toBeInTheDocument()
    expect(screen.queryByText(/À rapprocher/)).not.toBeInTheDocument()
    await user.click(within(block).getByRole("button", { name: "Valider le solde" }))

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1))
    expect(posted).toEqual(["4"])
    expect(await screen.findByText("Solde validé")).toBeInTheDocument()
  })

  it("validation refusée : message d'erreur, parent non prévenu, bouton de nouveau actif", async () => {
    server.use(http.post(apiUrl("/accounts/:id/verify"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const onChanged = vi.fn()
    const { user } = renderStep([account({ group: "market", statement_balance: null })], { onChanged })

    await user.click(screen.getByRole("button", { name: "Valider le solde" }))

    expect(await screen.findByText("Échec de la validation")).toBeInTheDocument()
    expect(onChanged).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: "Valider le solde" })).toBeEnabled()
  })
})

describe("CategorizeStep", () => {
  const categories = [makeCategory({ id: 3, name: "Courses", type: "depense" }), makeCategory({ id: 4, name: "Salaire", type: "revenu" }), makeCategory({ id: 5, name: "Loisirs", type: "depense" })]
  const serveCategories = () => server.use(http.get(apiUrl("/categories"), () => HttpResponse.json(categories)))

  it("toutes les dépenses catégorisées : message de réussite", () => {
    serveCategories()
    renderWithProviders(<CategorizeStep step={{ count: 0, total: 0, items: [] }} onChanged={vi.fn()} />, { auth: true })

    expect(screen.getByText("Toutes les dépenses du mois sont catégorisées.")).toBeInTheDocument()
  })

  it("liste les dépenses sans catégorie avec le total ; les catégories de revenu ne sont pas proposées", async () => {
    serveCategories()
    renderWithProviders(<CategorizeStep step={{ count: 2, total: 90, items: [tx(1, "Cinéma", 40), tx(2, "Boulangerie", 50)] }} onChanged={vi.fn()} />, { auth: true })

    expect(screen.getByText(/2 dépenses sans catégorie, soit/)).toBeInTheDocument()
    expect(screen.getByText(/90,00/)).toBeInTheDocument()
    const select = screen.getByLabelText("Catégorie de Cinéma")
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3))
    expect(within(select).queryByRole("option", { name: "Salaire" })).not.toBeInTheDocument()
  })

  it("plus de dépenses que de lignes affichées : l'étape l'indique", async () => {
    serveCategories()
    renderWithProviders(<CategorizeStep step={{ count: 30, total: 900, items: [tx(1, "Cinéma", 40)] }} onChanged={vi.fn()} />, { auth: true })

    expect(await screen.findByText(/30 dépenses sans catégorie/)).toBeInTheDocument()
    expect(screen.getByText(/Les 1 plus grosses sont listées\./)).toBeInTheDocument()
  })

  it("choisir une catégorie : PATCH de la transaction puis le parent est prévenu", async () => {
    serveCategories()
    const patched: { id: string; body: unknown }[] = []
    server.use(http.patch(apiUrl("/transactions/:id"), async ({ request, params }) => { patched.push({ id: String(params.id), body: await request.json() }); return HttpResponse.json({}) }))
    const onChanged = vi.fn()
    const { user } = renderWithProviders(<CategorizeStep step={{ count: 1, total: 40, items: [tx(1, "Cinéma", 40)] }} onChanged={onChanged} />, { auth: true })
    const select = screen.getByLabelText("Catégorie de Cinéma")
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3))

    await user.selectOptions(select, "Loisirs")

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1))
    expect(patched).toEqual([{ id: "1", body: { category_id: 5 } }])
    expect(await screen.findByText("Catégorie enregistrée")).toBeInTheDocument()
  })

  it("catégorisation refusée : message d'erreur, parent non prévenu", async () => {
    serveCategories()
    server.use(http.patch(apiUrl("/transactions/:id"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const onChanged = vi.fn()
    const { user } = renderWithProviders(<CategorizeStep step={{ count: 1, total: 40, items: [tx(1, "Cinéma", 40)] }} onChanged={onChanged} />, { auth: true })
    const select = screen.getByLabelText("Catégorie de Cinéma")
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3))

    await user.selectOptions(select, "Courses")

    expect(await screen.findByText("Échec de la catégorisation")).toBeInTheDocument()
    expect(onChanged).not.toHaveBeenCalled()
  })

  it("catégories indisponibles : la liste reste utilisable (vide)", async () => {
    server.use(http.get(apiUrl("/categories"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    renderWithProviders(<CategorizeStep step={{ count: 1, total: 40, items: [tx(1, "Cinéma", 40)] }} onChanged={vi.fn()} />, { auth: true })

    const select = screen.getByLabelText("Catégorie de Cinéma")
    expect(within(select).getAllByRole("option")).toHaveLength(1)
  })
})
