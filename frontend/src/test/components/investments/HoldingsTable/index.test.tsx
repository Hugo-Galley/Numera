/** Positions d'un compte titres : mode confidentialité (montants masqués) et option « titres et parts seulement ». */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { safeStorage } from "@/lib/storage"
import { renderWithProviders } from "@/test/support/render"
import { apiUrl } from "@/test/support/handlers"
import { server } from "@/test/support/server"
import type { PortfolioHolding } from "@/types/diversity"
import { HoldingsTable } from "@/components/investments/HoldingsTable"

const holding = (overrides: Partial<PortfolioHolding> = {}): PortfolioHolding => ({
  id: 1,
  account_id: 5,
  ticker: "CW8.PA",
  isin: "LU1681043599",
  asset_name: "Amundi MSCI World",
  quantity: 12.5,
  buy_price_avg: 480,
  currency: "EUR",
  current_price: 520.4,
  current_price_eur: 520.4,
  current_value_eur: 6505,
  total_invested_eur: 6000,
  gain_eur: 505,
  gain_pct: 8.42,
  is_etf: true,
  ...overrides,
})

const holdings = [holding(), holding({ id: 2, ticker: "AI.PA", isin: "FR0000120073", asset_name: "Air Liquide", quantity: 3, is_etf: false, current_value_eur: 540.3, total_invested_eur: 600, gain_eur: -59.7, gain_pct: -9.95 })]

function renderTable() {
  return renderWithProviders(<HoldingsTable accountId={5} accountName="PEA" holdings={holdings} onRefresh={vi.fn()} />, { auth: true })
}

/** Le tableau de bureau (la liste mobile est aussi rendue, masquée par CSS). */
const desktopTable = () => screen.getByRole("table")
const isMasked = (element: Element) => element.closest(".privacy-masked, .amount-blur") !== null

describe("HoldingsTable : confidentialité", () => {
  it("hors confidentialité, les montants sont affichés en clair", () => {
    renderTable()
    const value = within(desktopTable()).getByText(/6\s505,00\s€/)

    expect(document.body).not.toHaveClass("privacy-enabled")
    expect(value).toBeVisible()
    expect(value.closest(".privacy-masked")).toBeNull()
  })

  it("en mode confidentialité, chaque montant est masqué mais titres et parts restent lisibles", async () => {
    safeStorage.setItem("privacy-mode", "true")
    renderTable()
    const table = desktopTable()

    expect(document.body).toHaveClass("privacy-enabled")
    const amounts = [/6\s505,00\s€/, /6\s000,00\s€/, /\+505,00\s€/, /540,30\s€/, /-59,70\s€/, /520,40\s€/]
    await waitFor(() => {
      for (const amount of amounts) {
        for (const element of within(table).getAllByText(amount)) expect(isMasked(element)).toBe(true)
      }
    })
    expect(isMasked(within(table).getByText("CW8.PA"))).toBe(false)
    expect(isMasked(within(table).getByText("12.5"))).toBe(false)
  })

  it("l'option « titres et parts seulement » retire tous les montants", () => {
    safeStorage.setItem("hide-holding-values", "true")
    renderTable()
    const table = desktopTable()

    expect(screen.getByText("Titres détenus et nombre de parts.")).toBeInTheDocument()
    expect(within(table).queryByRole("columnheader", { name: "Valeur totale" })).not.toBeInTheDocument()
    expect(within(table).queryByText(/€/)).not.toBeInTheDocument()
    expect(within(table).getByText("Amundi MSCI World")).toBeInTheDocument()
    expect(within(table).getByText("12.5")).toBeInTheDocument()
  })
})

describe("HoldingsTable : fiche ETF", () => {
  it("le nom d'une position rattachée à un fonds mène à sa fiche, pas celui d'une action", () => {
    renderWithProviders(
      <HoldingsTable accountId={5} accountName="PEA" holdings={[holding({ etf_profile_id: 4 }), holdings[1]]} onRefresh={vi.fn()} />,
      { auth: true },
    )

    expect(within(desktopTable()).getByRole("link", { name: "Amundi MSCI World" })).toHaveAttribute("href", "/investments/etf/4")
    expect(within(desktopTable()).queryByRole("link", { name: "Air Liquide" })).not.toBeInTheDocument()
    // La liste mobile a le même lien
    expect(screen.getAllByRole("link", { name: "Amundi MSCI World" })).toHaveLength(2)
  })
})

describe("HoldingsTable : ISIN à compléter", () => {
  const missing = holding({ id: 3, ticker: "HO.PA", isin: undefined, asset_name: "Thales", is_etf: false, isin_missing: true })

  function renderMissing(...rows: PortfolioHolding[]) {
    const onRefresh = vi.fn()
    const view = renderWithProviders(<HoldingsTable accountId={5} accountName="PEA" holdings={rows} onRefresh={onRefresh} />, { auth: true })
    return { ...view, onRefresh }
  }

  /** Corps des enregistrements reçus par l'API. */
  function recordUpdates() {
    const bodies: unknown[] = []
    server.use(http.put(apiUrl("/holdings/3"), async ({ request }) => {
      bodies.push(await request.json())
      return HttpResponse.json({ id: 3 })
    }))
    return bodies
  }

  it("signale la position sans ISIN, sur bureau et sur mobile, et elle seule", () => {
    renderMissing(missing, holding({ isin_missing: false }), holding({ id: 4, ticker: "BTC-EUR", isin: undefined, isin_missing: false }))

    expect(screen.getAllByRole("button", { name: "ISIN à compléter" })).toHaveLength(2)
    expect(within(desktopTable()).getAllByRole("button", { name: "ISIN à compléter" })).toHaveLength(1)
  })

  it("ouvre la saisie au clic puis enregistre l'ISIN en majuscules", async () => {
    const bodies = recordUpdates()
    const { user, onRefresh } = renderMissing(missing)

    await user.click(within(desktopTable()).getByRole("button", { name: "ISIN à compléter" }))
    await user.type(within(desktopTable()).getByRole("textbox", { name: "ISIN de HO.PA" }), " fr0000121329 {Enter}")

    await waitFor(() => expect(onRefresh).toHaveBeenCalled())
    expect(bodies).toEqual([{ isin: "FR0000121329" }])
    expect(await screen.findByText("ISIN de HO.PA enregistré")).toBeInTheDocument()
  })

  it("refuse un ISIN mal formé sans rien envoyer", async () => {
    const bodies = recordUpdates()
    const { user, onRefresh } = renderMissing(missing)

    await user.click(within(desktopTable()).getByRole("button", { name: "ISIN à compléter" }))
    await user.type(within(desktopTable()).getByRole("textbox", { name: "ISIN de HO.PA" }), "FR00001{Enter}")

    expect(await screen.findByText("Un ISIN compte 12 caractères : 2 lettres, 9 lettres ou chiffres, 1 chiffre")).toBeInTheDocument()
    expect(bodies).toEqual([])
    expect(onRefresh).not.toHaveBeenCalled()
  })

  it("Échap abandonne la saisie", async () => {
    const { user } = renderMissing(missing)

    await user.click(within(desktopTable()).getByRole("button", { name: "ISIN à compléter" }))
    await user.keyboard("{Escape}")

    expect(within(desktopTable()).queryByRole("textbox", { name: "ISIN de HO.PA" })).not.toBeInTheDocument()
    expect(within(desktopTable()).getByRole("button", { name: "ISIN à compléter" })).toBeInTheDocument()
  })
})
