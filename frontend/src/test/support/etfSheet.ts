/** Fiche ETF de test (réponse de `/etf-profiles/{id}/constituents`). */
import type { EtfSheet, EtfSheetLine } from "@/pages/EtfSheet/types"

export const makeSheetLine = (extra: Partial<EtfSheetLine> = {}): EtfSheetLine => ({
  name: "Société", ticker: null, isin: null, weight: 1, country: "USA", sector: "Technologie", asset_class: "Equity", exposure_eur: 0, ...extra,
})

export const makeEtfSheet = (extra: Partial<EtfSheet> = {}): EtfSheet => ({
  profile: {
    id: 1, name: "iShares Core MSCI World", ticker: "EUNL.DE", isin: "IE00B4L5Y983", aliases: [], countries: {},
    sectors: {}, top_holdings: [], is_system: false, composition_sources: { countries: "ishares" },
    replication: "physical", index_name: "MSCI World", lines_count: 3,
    created_at: "2026-11-01T00:00:00", updated_at: "2026-11-27T00:00:00",
  },
  exposure_profile_id: null,
  exposure_profile_name: null,
  provider: "ishares",
  composition_as_of: "2026-11-25",
  coverage_pct: 99.8,
  lines_count: 3,
  has_full_list: true,
  held_value_eur: 2000,
  countries: [{ name: "USA", weight: 70 }, { name: "JPN", weight: 30 }],
  sectors: [{ name: "Technologie", weight: 100 }],
  lines: [
    makeSheetLine({ name: "Apple", ticker: "AAPL", isin: "US0378331005", weight: 5, exposure_eur: 100 }),
    makeSheetLine({ name: "Sony", country: "JPN", weight: 2 }),
    makeSheetLine({ name: "Nestlé", country: "CHE", sector: "Consommation de base", weight: 1 }),
  ],
  top_holdings: [],
  ...extra,
})
