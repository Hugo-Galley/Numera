/** Revue de fin de mois : validation des soldes des comptes et catégorisation des dépenses restantes. */
import { screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { makeCategory } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { AccountsStep } from "@/components/month-review/AccountsStep"
import { CategorizeStep } from "@/components/month-review/CategorizeStep"
import type { MonthReview } from "@/types/monthReview"

const account = (overrides: Partial<MonthReview["accounts"]["accounts"][number]> = {}) => ({
  id: 1, name: "Compte courant", currency: "EUR", balance: 1234.5, last_verified_at: "2026-05-28T10:00:00", verified_since_month_end: false, ...overrides,
})
const tx = (id: number, merchant: string, amount: number) => ({ id, date: "2026-06-12T10:00:00", merchant, amount, category_name: null, is_exceptional: false })

describe("AccountsStep", () => {
  const step = (accounts: ReturnType<typeof account>[]) => ({ unverified_count: accounts.filter((a) => !a.verified_since_month_end).length, accounts })

  it("liste chaque compte avec son solde et la date de dernière validation ; un compte déjà validé n'a pas de bouton", () => {
    renderWithProviders(
      <AccountsStep step={step([account(), account({ id: 2, name: "Livret A", balance: 5000, verified_since_month_end: true })])} onChanged={vi.fn()} />,
      { auth: true },
    )

    expect(screen.getByText("Compte courant")).toBeInTheDocument()
    expect(screen.getByText(/1\s234,50/)).toBeInTheDocument()
    expect(screen.getAllByText(/Dernière validation/)).toHaveLength(2)
    expect(screen.getAllByRole("button", { name: "Valider le solde" })).toHaveLength(1)
    expect(screen.getByText("Validé")).toBeInTheDocument()
  })

  it("« Valider le solde » : POST de vérification puis le parent est prévenu", async () => {
    const posted: string[] = []
    server.use(http.post(apiUrl("/accounts/:id/verify"), ({ params }) => { posted.push(String(params.id)); return HttpResponse.json({}) }))
    const onChanged = vi.fn()
    const { user } = renderWithProviders(<AccountsStep step={step([account()])} onChanged={onChanged} />, { auth: true })

    await user.click(screen.getByRole("button", { name: "Valider le solde" }))

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1))
    expect(posted).toEqual(["1"])
    expect(await screen.findByText("Solde validé")).toBeInTheDocument()
  })

  it("validation refusée : message d'erreur, parent non prévenu, bouton de nouveau actif", async () => {
    server.use(http.post(apiUrl("/accounts/:id/verify"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const onChanged = vi.fn()
    const { user } = renderWithProviders(<AccountsStep step={step([account()])} onChanged={onChanged} />, { auth: true })

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
