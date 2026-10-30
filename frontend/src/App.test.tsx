/** Table des routes d'`App.tsx` (son propre BrowserRouter) : pages remplacées par des pages factices. */
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { safeStorage } from "@/lib/storage"
import { makeToken } from "@/test/token"
import { NAVIGATION } from "@/components/layout/Omnibox/types"
import { App } from "./App"

vi.mock("@/components/layout/AppLayout", async () => {
  const { Outlet } = await import("react-router-dom")
  const { Sidebar } = await import("@/components/layout/Sidebar")
  return {
    AppLayout: () => (
      <div>
        <Sidebar />
        <main>
          <Outlet />
        </main>
      </div>
    ),
  }
})

const { stub } = vi.hoisted(() => ({
  stub: (title: string) => async () => {
    const { stubPage } = await import("@/test/LocationDisplay")
    return { default: stubPage(title) }
  },
}))
vi.mock("@/pages/Login", stub("Page Connexion"))
vi.mock("@/pages/Dashboard", stub("Page Tableau de bord"))
vi.mock("@/pages/Accounts", stub("Page Comptes"))
vi.mock("@/pages/AccountDetail", stub("Page Détail du compte"))
vi.mock("@/pages/Savings", stub("Page Épargne"))
vi.mock("@/pages/Investments", stub("Page Investissements"))
vi.mock("@/pages/MonthHub", stub("Page Mois"))
vi.mock("@/pages/MonthlyReport", stub("Onglet Bilan"))
vi.mock("@/pages/MonthReview", stub("Onglet Revue"))
vi.mock("@/pages/Comparison", stub("Onglet Comparaison"))
vi.mock("@/pages/RecurringTransactions", stub("Page Échéances"))
vi.mock("@/pages/Reimbursements", stub("Page Remboursements"))
vi.mock("@/pages/Wrapped", stub("Page Bilan annuel"))
vi.mock("@/pages/Audit", stub("Page Centre d'actions"))
vi.mock("@/pages/Tools", stub("Page Simulateur"))
vi.mock("@/pages/Tax", stub("Page Fiscalité"))
vi.mock("@/pages/Classement", stub("Page Classement"))
vi.mock("@/pages/Settings", stub("Page Paramètres"))
vi.mock("@/pages/NotFound", stub("Page introuvable"))

function renderApp(url: string, { auth = true } = {}) {
  if (auth) safeStorage.setItem("token", makeToken())
  window.history.replaceState(null, "", url)
  return { user: userEvent.setup(), ...render(<App />) }
}

/** Adresse affichée par la page factice la plus profonde (onglet de « Mois » compris). */
const address = () => {
  const outputs = screen.getAllByRole("status", { name: "adresse" })
  return outputs[outputs.length - 1].textContent
}

afterAll(() => window.history.replaceState(null, "", "/"))

describe("App : anciennes adresses", () => {
  it.each([
    ["/report?year=2026&month=5", "Onglet Bilan", "/month/bilan?year=2026&month=5"],
    ["/month-review?year=2026&month=5", "Onglet Revue", "/month/revue?year=2026&month=5"],
    ["/comparison?month=5", "Onglet Comparaison", "/month/comparaison?month=5"],
    ["/calendar?month=2026-05", "Page Échéances", "/recurring?month=2026-05&tab=calendar"],
    ["/calendar?tab=list&month=5", "Page Échéances", "/recurring?tab=calendar&month=5"],
  ])("%s → %s en gardant la query", async (url, page, expected) => {
    renderApp(url)

    expect(await screen.findByRole("heading", { name: page })).toBeInTheDocument()
    expect(address()).toBe(expected)
    expect(window.location.pathname + window.location.search).toBe(expected)
  })

  it("sans query, l'ancienne adresse redirige sans « ? » final", async () => {
    renderApp("/report")

    expect(await screen.findByRole("heading", { name: "Onglet Bilan" })).toBeInTheDocument()
    expect(address()).toBe("/month/bilan")
  })

  it("/month ouvre l'onglet Bilan", async () => {
    renderApp("/month")

    expect(await screen.findByRole("heading", { name: "Onglet Bilan" })).toBeInTheDocument()
    expect(address()).toBe("/month/bilan")
  })

  it("sans session, une ancienne adresse mène à la connexion", async () => {
    renderApp("/report?month=5", { auth: false })

    expect(await screen.findByRole("heading", { name: "Page Connexion" })).toBeInTheDocument()
    expect(address()).toBe("/login")
  })
})

describe("App : route inconnue", () => {
  // `frontend/src/CLAUDE.md` annonce « Route inconnue → / » : l'app affiche en fait la page NotFound
  // (dans le layout, lien « Retour au tableau de bord »), sans changer l'adresse.
  it("affiche la page introuvable dans le layout, à la même adresse", async () => {
    renderApp("/nimporte-quoi?x=1")

    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument()
    expect(address()).toBe("/nimporte-quoi?x=1")
    expect(screen.getByRole("navigation")).toBeInTheDocument()
  })
})

describe("App : Sidebar", () => {
  it("compte 12 entrées en 3 groupes", async () => {
    renderApp("/")
    await screen.findByRole("heading", { name: "Page Tableau de bord" })

    expect(within(screen.getByRole("navigation")).getAllByRole("link")).toHaveLength(12)
  })

  it("chaque entrée mène à une route déclarée (jamais la page introuvable)", async () => {
    const { user } = renderApp("/")
    await screen.findByRole("heading", { name: "Page Tableau de bord" })
    const nav = () => within(screen.getByRole("navigation"))
    const names = nav().getAllByRole("link").map((link) => link.textContent ?? "")
    const visited: string[] = []

    for (const name of names) {
      const link = nav().getByRole("link", { name })
      const href = link.getAttribute("href")
      await user.click(link)
      // « Mois » ouvre son premier onglet (/month/bilan)
      await waitFor(() => expect(window.location.pathname).toMatch(new RegExp(`^${href}(/|$)`)))
      const [heading] = await screen.findAllByRole("heading", { level: 1 })
      expect(heading, `${name} (${href})`).not.toHaveTextContent("Page introuvable")
      visited.push(`${href} → ${heading.textContent}`)
    }

    expect(visited).toEqual([
      "/ → Page Tableau de bord",
      "/month → Page Mois",
      "/wrapped → Page Bilan annuel",
      "/audit → Page Centre d'actions",
      "/accounts → Page Comptes",
      "/savings → Page Épargne",
      "/investments → Page Investissements",
      "/tax → Page Fiscalité",
      "/recurring → Page Échéances",
      "/reimbursements → Page Remboursements",
      "/classement → Page Classement",
      "/tools → Page Simulateur",
    ])
  })
})

describe("App : destinations de l'Omnibox", () => {
  it.each(NAVIGATION.map((item) => [item.name, item.href]))("« %s » (%s) mène à une route déclarée", async (_, href) => {
    renderApp(href)

    const [heading] = await screen.findAllByRole("heading", { level: 1 })
    expect(heading).not.toHaveTextContent("Page introuvable")
  })
})
