/** En-tête du tableau de bord : état « mois en cours », filtres compacts sur mobile, raccourci explicite vers le compte principal. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { DashboardHeader } from "@/components/dashboard/DashboardHeader"
import type { DashboardAccount } from "@/components/dashboard/types"
import { partial } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

const accounts = [
  partial<DashboardAccount>({ id: 1, name: "Compte courant", active: true, is_main: true, currency: "EUR" }),
  partial<DashboardAccount>({ id: 2, name: "Livret A", active: true, is_main: false, currency: "EUR" }),
]

const header = (props: Partial<Parameters<typeof DashboardHeader>[0]> = {}) =>
  renderWithProviders(
    <DashboardHeader
      accounts={accounts}
      selectedAccountId="all"
      setSelectedAccountId={vi.fn()}
      month={11}
      setMonth={vi.fn()}
      year={2026}
      setYear={vi.fn()}
      {...props}
    />,
    { auth: true },
  )

// Logos des comptes (AccountLogo) : lus via /accounts
beforeEach(() => server.use(http.get(apiUrl("/accounts"), () => HttpResponse.json(accounts))))

describe("DashboardHeader", () => {
  it("période en cours : badge « Mois en cours · J23/30 »", () => {
    header({ progress: { day: 23, total: 30 } })

    expect(screen.getByText("Mois en cours · J23/30")).toBeInTheDocument()
  })

  it("période terminée : pas de badge", () => {
    header({ progress: null })

    expect(screen.queryByText(/Mois en cours/)).not.toBeInTheDocument()
  })

  it("mobile : une ligne résume compte et mois, et déplie les filtres", async () => {
    const { user } = header()

    const toggle = screen.getByRole("button", { name: "Afficher les filtres (compte, mois, année)" })
    expect(toggle).toHaveTextContent("Tous les comptes · Novembre 2026")
    expect(toggle).toHaveAttribute("aria-expanded", "false")
    await user.click(toggle)
    expect(toggle).toHaveAttribute("aria-expanded", "true")
    expect(document.getElementById("dashboard-filters")?.className).toMatch(/(^|\s)grid(\s|$)/)
  })

  it("compte principal : lien libellé (et plus une étoile muette)", () => {
    header()

    const link = screen.getByRole("link", { name: "Ouvrir le compte principal : Compte courant" })
    expect(link).toHaveAttribute("href", "/accounts/1")
    expect(link).toHaveTextContent("Compte principal")
  })
})
