import { appLocale } from "@/i18n/locale"

export const COUNTRIES = [
  { name: "France", code: "FRA" },
  { name: "États-Unis", code: "USA" },
  { name: "Allemagne", code: "DEU" },
  { name: "Royaume-Uni", code: "GBR" },
  { name: "Japon", code: "JPN" },
  { name: "Chine", code: "CHN" },
  { name: "Canada", code: "CAN" },
  { name: "Suisse", code: "CHE" },
  { name: "Luxembourg", code: "LUX" },
  { name: "Pays-Bas", code: "NLD" },
  { name: "Belgique", code: "BEL" },
  { name: "Espagne", code: "ESP" },
  { name: "Italie", code: "ITA" },
  { name: "Brésil", code: "BRA" },
  { name: "Inde", code: "IND" },
  { name: "Australie", code: "AUS" },
  { name: "Irlande", code: "IRL" },
  { name: "Singapour", code: "SGP" },
  { name: "Hong Kong", code: "HKG" },
  { name: "Taïwan", code: "TWN" },
  { name: "Corée du Sud", code: "KOR" },
  { name: "Monde (ETF World)", code: "WORLD" }
];

// Codes alpha-3 des compositions d'ETF (`backend/app/domain/etf_presets.json`) et voisins courants → alpha-2 pour `Intl.DisplayNames`
const ALPHA3_TO_ALPHA2: Record<string, string> = {
  ARE: "AE", ARG: "AR", AUS: "AU", AUT: "AT", BEL: "BE", BRA: "BR", CAN: "CA", CHE: "CH", CHL: "CL", CHN: "CN",
  COL: "CO", CZE: "CZ", DEU: "DE", DNK: "DK", EGY: "EG", ESP: "ES", FIN: "FI", FRA: "FR", GBR: "GB", GRC: "GR",
  HKG: "HK", HUN: "HU", IDN: "ID", IND: "IN", IRL: "IE", ISR: "IL", ITA: "IT", JPN: "JP", KOR: "KR", KWT: "KW",
  LUX: "LU", MEX: "MX", MYS: "MY", NLD: "NL", NOR: "NO", NZL: "NZ", PER: "PE", PHL: "PH", POL: "PL", PRT: "PT",
  QAT: "QA", SAU: "SA", SGP: "SG", SWE: "SE", THA: "TH", TUR: "TR", TWN: "TW", USA: "US", ZAF: "ZA",
}

/**
 * Nom d'un pays d'après son code ISO 3166-1 alpha-3 (« USA », « FRA »), dans la langue de l'interface.
 * Un code inconnu, ou un libellé qui n'est pas un code (« Autres »), est rendu tel quel.
 */
export function countryName(code: string): string {
  const alpha2 = ALPHA3_TO_ALPHA2[code.toUpperCase()]
  if (!alpha2) return code
  try {
    return new Intl.DisplayNames([appLocale()], { type: "region" }).of(alpha2) ?? code
  } catch {
    return code
  }
}
