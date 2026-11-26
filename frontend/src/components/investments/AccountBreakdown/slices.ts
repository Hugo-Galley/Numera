/**
 * Parts du donut de répartition d'un compte : les plus grosses lignes nommées, le reste regroupé en « Autres ».
 * Présentation seulement (tri, part en % du graphique) : les montants viennent de `/analytics/diversity-scanner`.
 */
import { CATEGORY_COLORS, NEUTRAL_COLOR, UNCLASSIFIED_NAME } from "@/lib/chartPalette"

/** Nombre de parts nommées avant le regroupement (une couleur chacune, palette de 8 sans le gris). */
export const MAX_NAMED_SLICES = 7

/** Libellés renvoyés par le backend pour une part sans classification : toujours regroupés dans « Autres ». */
const UNCLASSIFIED_LABELS = new Set(["Non renseigné", "Autres", UNCLASSIFIED_NAME])

export interface BreakdownRow {
  name: string | null | undefined
  value: number
  ticker?: string | null
}

export interface Slice {
  key: string
  name: string
  value: number
  /** Part de la valeur des positions du compte, en % */
  share: number
  color: string
  ticker?: string
  isOther: boolean
}

/**
 * `total` : valeur des positions du compte. Ce qui n'est pas couvert par les lignes nommées retenues (lignes au-delà
 * des 7 premières, part non décomposée d'un ETF, libellés non classés) forme la part « Autres ».
 */
export function buildSlices(rows: BreakdownRow[], total: number, otherLabel: string): Slice[] {
  if (total <= 0) return []
  const named = rows
    .filter((r) => r.value > 0 && r.name && !UNCLASSIFIED_LABELS.has(r.name))
    .sort((a, b) => b.value - a.value)
    .slice(0, MAX_NAMED_SLICES)
  const slices: Slice[] = named.map((r, i) => ({
    key: `${i}-${r.name}`,
    name: r.name as string,
    value: r.value,
    share: (r.value / total) * 100,
    color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
    ticker: r.ticker ?? undefined,
    isOther: false,
  }))
  const rest = total - named.reduce((sum, r) => sum + r.value, 0)
  // Sous 0,1 % : arrondis des parts, pas une vraie ligne
  if (rest / total > 0.001) {
    slices.push({ key: "other", name: otherLabel, value: rest, share: (rest / total) * 100, color: NEUTRAL_COLOR, isOther: true })
  }
  return slices
}
