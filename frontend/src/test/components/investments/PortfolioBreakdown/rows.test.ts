/** Vues et lignes du donut : mêmes règles que le scanner de diversification (secteurs, pays, provenance). */
import { rowsFor, viewsFor, type BreakdownData } from "@/components/investments/PortfolioBreakdown/rows"

const data = (extra: Partial<BreakdownData> = {}): BreakdownData => ({
  totals: { stocks_eur: 1000, direct_eur: 1000, etf_eur: 0, holdings_count: 2, etfs_count: 0 },
  top_underlying_companies: [],
  holdings: [],
  sectors: [],
  countries: [],
  ...extra,
})

describe("viewsFor", () => {
  it("propose secteurs et pays dès qu'il y a des données, même sans aucun ETF", () => {
    expect(viewsFor(data({ sectors: [{ name: "Technologie", value_eur: 800 }], countries: [{ name: "USA", value_eur: 800 }] })))
      .toEqual(["companies", "sectors", "countries"])
  })

  it("propose chaque vue seulement si elle a une valeur", () => {
    expect(viewsFor(data({ sectors: [{ name: "Crypto-actifs", value_eur: 500 }] }))).toEqual(["companies", "sectors"])
    expect(viewsFor(data({ countries: [{ name: "USA", value_eur: 0 }] }))).toEqual(["companies"])
  })
})

describe("rowsFor", () => {
  it("garde tels quels les postes du backend qui ne sont pas des codes pays", () => {
    const countries = ["USA", "Liquidités et dérivés", "Crypto-actifs", "Non renseigné"].map((name) => ({ name, value_eur: 10 }))
    expect(rowsFor(data({ countries }), "countries", "all").map((r) => r.name))
      .toEqual(["États-Unis", "Liquidités et dérivés", "Crypto-actifs", "Non renseigné"])
  })

  it("filtre les positions comme la transparence du backend : avec un profil, via ETF ; sinon (crypto comprise), en direct", () => {
    const holdings = [
      { ticker: "CW8.PA", name: "World", value_eur: 500, etf_profile_id: 1 },
      { ticker: "BTC-EUR", name: "Bitcoin", value_eur: 300, etf_profile_id: null },
      { ticker: "TTE.PA", name: "Total", value_eur: 200, etf_profile_id: null },
    ]
    const names = (source: "direct" | "etf") => rowsFor(data({ holdings }), "positions", source).map((r) => r.name)
    expect(names("direct")).toEqual(["Bitcoin", "Total"])
    expect(names("etf")).toEqual(["World"])
  })
})
