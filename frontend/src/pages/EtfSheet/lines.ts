/** Recherche et tri des lignes déjà chargées d'un fonds (présentation seulement). */
import { appLocale } from "@/i18n/locale"
import { countryName } from "@/lib/countries"

export type LineSort = "weight" | "name" | "country" | "sector"

export interface DisplayLine {
  key: number
  name: string
  ticker?: string | null
  isin?: string | null
  weight: number
  country?: string | null
  sector?: string | null
}

export function searchLines(lines: DisplayLine[], query: string): DisplayLine[] {
  const needle = query.trim().toLowerCase()
  if (!needle) return lines
  return lines.filter((l) => [l.name, l.ticker, l.isin].some((v) => v?.toLowerCase().includes(needle)))
}

/** Poids décroissant, sinon ordre alphabétique de ce qui est affiché (valeurs inconnues à la fin) ; à égalité, le poids. */
export function sortLines(lines: DisplayLine[], sort: LineSort): DisplayLine[] {
  const byWeight = (a: DisplayLine, b: DisplayLine) => b.weight - a.weight
  if (sort === "weight") return [...lines].sort(byWeight)
  const collator = new Intl.Collator(appLocale())
  const label = (l: DisplayLine) => (sort === "country" ? l.country && countryName(l.country) : l[sort]) ?? ""
  return lines
    .map((line) => ({ line, text: label(line) }))
    .sort((a, b) => Number(!a.text) - Number(!b.text) || collator.compare(a.text, b.text) || byWeight(a.line, b.line))
    .map((x) => x.line)
}
