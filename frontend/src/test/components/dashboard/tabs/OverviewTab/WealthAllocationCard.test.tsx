/** Répartition du patrimoine : la liste garde sa hauteur naturelle (pas de défilement interne) tant qu'elle est courte. */
import { screen } from "@testing-library/react"
import type { PatrimoineAllocation } from "@/components/dashboard/types"
import { WealthAllocationCard } from "@/components/dashboard/tabs/OverviewTab/WealthAllocationCard"
import { SCROLL_THRESHOLD } from "@/components/dashboard/tabs/OverviewTab/WealthDetails"
import { useOverviewTab } from "@/components/dashboard/tabs/OverviewTab/useOverviewTab"
import { partial } from "@/test/support/factories"
import { renderWithProviders } from "@/test/support/render"

const item = (account_id: number, account_name: string, type = "investissement") => ({
  account_id, account_name, type, balance: 1000, balance_eur: 1000, currency: "EUR", institution: "Banque",
})
const allocation = (n: number) =>
  partial<PatrimoineAllocation>({
    total_patrimoine: n * 1000, total_debts_eur: 0, net_patrimoine_eur: n * 1000,
    items: Array.from({ length: n }, (_, i) => item(i + 1, i === 0 ? "Assurance-vie - Investissement long terme" : `Compte ${i + 1}`)),
  })

function Card({ data }: { data: PatrimoineAllocation }) {
  const ctx = useOverviewTab(null, [], "EUR", [], data, { month: 11, year: 2026, accountId: null })
  return <WealthAllocationCard ctx={ctx} />
}

const list = () => screen.getByTestId("wealth-details")

describe("WealthAllocationCard : liste du patrimoine", () => {
  it("peu de lignes : hauteur naturelle, aucune zone défilante (la molette ne s'y bloque pas)", () => {
    renderWithProviders(<Card data={allocation(4)} />, { auth: true })

    expect(list().className).not.toMatch(/overflow-y-auto/)
    expect(list().className).not.toMatch(/max-h-/)
  })

  it("au-delà du seuil : la liste défile dans sa carte", () => {
    renderWithProviders(<Card data={allocation(SCROLL_THRESHOLD + 1)} />, { auth: true })

    expect(list().className).toMatch(/md:overflow-y-auto/)
  })

  it("nom de compte affiché en entier (retour à la ligne, pas de troncature)", () => {
    renderWithProviders(<Card data={allocation(2)} />, { auth: true })

    const name = screen.getByText("Assurance-vie - Investissement long terme")
    expect(name.className).not.toMatch(/\btruncate\b/)
  })

  it("onglets de regroupement : cible tactile d'au moins 40 px sur mobile", () => {
    renderWithProviders(<Card data={allocation(2)} />, { auth: true })

    for (const name of ["Par Catégorie", "Mixte", "Par Compte", "Par Établissement"]) {
      expect(screen.getByRole("tab", { name }).className).toMatch(/(^|\s)min-h-10(\s|$)/)
    }
  })
})
