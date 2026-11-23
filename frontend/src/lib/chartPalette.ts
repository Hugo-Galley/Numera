/**
 * Palette catégorielle des graphiques de répartition (comptes, classes d'actifs, secteurs, treemap).
 *
 * Teintes moyennes en hexadécimal, lisibles sur fond clair comme sur fond sombre (contraste ≥ 3:1 avec le blanc
 * et avec l'ardoise 900) : elles ne passent pas par les variables de thème, donc restent valables en
 * `style={{ backgroundColor }}` où `styles.css` n'inverse rien. Pas de gris (réservé au « Non classé ») ni de rose
 * (réservé aux pertes).
 */
export const CATEGORY_COLORS = [
  "#6366f1", // indigo 500
  "#059669", // emerald 600
  "#d97706", // amber 600
  "#ec4899", // pink 500
  "#0891b2", // cyan 600
  "#8b5cf6", // violet 500
  "#ea580c", // orange 600
  "#65a30d", // lime 600
] as const

/** Couleur neutre (ardoise 500) des parts non classées. */
export const NEUTRAL_COLOR = "#64748b"

/** Libellé renvoyé par le backend pour une part sans classification (`domain/investments.py::UNCLASSIFIED`). */
export const UNCLASSIFIED_NAME = "Non classé"

/** Couleur de la `index`-ième catégorie ; une part « Non classé » est toujours neutre. */
export function categoryColor(index: number, name?: string | null): string {
  if (name === UNCLASSIFIED_NAME) return NEUTRAL_COLOR
  return CATEGORY_COLORS[index % CATEGORY_COLORS.length]
}
