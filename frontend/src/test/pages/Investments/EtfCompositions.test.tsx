/** Origine des compositions : source, date, couverture et mention des ETF synthétiques. */
import { screen, within } from "@testing-library/react"
import { setLanguage } from "@/i18n"
import { EtfCompositions } from "@/pages/Investments/EtfCompositions"
import type { InvestmentsCtx } from "@/pages/Investments/useInvestments"
import type { EtfCompositionInfo } from "@/types/diversity"
import { renderWithProviders } from "@/test/support/render"

// La carte du monde va chercher son fond sur un site tiers : hors sujet ici
vi.mock("@/components/ui/WorldMap", () => ({ default: () => null }))

const composition = (overrides: Partial<EtfCompositionInfo> = {}): EtfCompositionInfo => ({
  profile_id: 1,
  profile_name: "iShares Core MSCI World",
  tickers: ["IWDA.L"],
  value_eur: 1000,
  sources: { countries: "ishares", sectors: "ishares", top_holdings: "ishares" },
  refreshed_at: "2026-11-26T06:00:00",
  provider: "ishares",
  replication: "physical",
  index_name: "MSCI World",
  exposure_profile_id: null,
  exposure_profile_name: null,
  composition_as_of: "2026-11-25",
  coverage_pct: 99.8,
  lines_count: 1273,
  ...overrides,
})

function renderCard(...compositions: EtfCompositionInfo[]) {
  const ctx = {
    advancedAllocation: null,
    diversity: { countries: [], etf_compositions: compositions },
    refreshCompositions: vi.fn(),
    refreshingCompositions: false,
  } as unknown as InvestmentsCtx
  return renderWithProviders(<EtfCompositions ctx={ctx} />)
}

describe("EtfCompositions : source, date et couverture", () => {
  it("affiche la source, la date de la composition et la part du fonds décrite", () => {
    renderCard(composition())

    expect(screen.getByText("iShares · composition au 25/11/2026")).toBeInTheDocument()
    expect(screen.getByText("1 273 lignes · 100 % du fonds")).toBeInTheDocument()
    expect(screen.getByText("Pays : iShares")).toBeInTheDocument()
    expect(screen.queryByText(/Synthétique/)).not.toBeInTheDocument()
    expect(screen.getByText("Compositions publiées par les émetteurs, actualisées chaque jour. La part non couverte apparaît en « Non renseigné ».")).toBeInTheDocument()
  })

  it("dit par quel ETF de référence un synthétique est décomposé", () => {
    renderCard(composition({
      profile_name: "Amundi MSCI World Swap", replication: "synthetic", exposure_profile_id: 7,
      exposure_profile_name: "iShares Core MSCI World",
    }))

    expect(screen.getByText("Synthétique : exposition de l'indice MSCI World via iShares Core MSCI World")).toBeInTheDocument()
  })

  it("signale un synthétique d'indice inconnu, sans chiffre de couverture", () => {
    renderCard(composition({
      provider: "amundi", replication: "synthetic", index_name: null, composition_as_of: null,
      coverage_pct: 0, lines_count: 0, sources: {},
    }))

    expect(screen.getByText("Synthétique : indice non reconnu, répartition indisponible")).toBeInTheDocument()
    expect(screen.queryByText(/du fonds/)).not.toBeInTheDocument()
    expect(screen.queryByText(/composition au/)).not.toBeInTheDocument()
  })

  it("sans le détail des lignes, annonce le top 10", () => {
    renderCard(composition({ provider: "justetf", coverage_pct: 42.3, lines_count: 0, sources: { top_holdings: "justetf" } }))

    expect(screen.getByText("justETF · composition au 25/11/2026")).toBeInTheDocument()
    expect(screen.getByText("Top 10 · 42 % du fonds")).toBeInTheDocument()
    expect(screen.getByText("Top 10 : justETF")).toBeInTheDocument()
  })

  it.each([
    ["amundi", "Amundi"],
    ["spdr", "SPDR"],
    ["yahoo", "Yahoo"],
  ] as const)("nomme la source %s", (provider, label) => {
    renderCard(composition({ provider }))

    expect(screen.getByText(`${label} · composition au 25/11/2026`)).toBeInTheDocument()
  })

  it("une saisie manuelle seule n'a ni source datée ni couverture", () => {
    renderCard(composition({
      provider: null, composition_as_of: null, coverage_pct: null, lines_count: 0, refreshed_at: null,
      sources: { countries: "manual" },
    }))

    const row = screen.getByText("iShares Core MSCI World").parentElement!
    expect(within(row).getByText(/jamais actualisé/)).toBeInTheDocument()
    expect(within(row).queryByText(/du fonds/)).not.toBeInTheDocument()
    expect(screen.getByText("Pays : Saisie")).toBeInTheDocument()
  })

  it("se traduit en anglais", () => {
    setLanguage("en")
    try {
      renderCard(composition({ lines_count: 1 }))

      expect(screen.getByText("iShares · composition as of 25/11/2026")).toBeInTheDocument()
      expect(screen.getByText("1 line · 100% of the fund")).toBeInTheDocument()
    } finally {
      setLanguage("fr")
    }
  })
})
