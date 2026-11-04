/** Première année proposée dans les sélecteurs de période. */
export const FIRST_YEAR = 2020

/** Années d'un sélecteur : de `FIRST_YEAR` à l'année courante, plus les valeurs sélectionnées (jamais un `Select` vide). */
export function yearOptions(...selected: string[]): number[] {
  const current = new Date().getFullYear()
  const years = new Set<number>()
  for (let y = FIRST_YEAR; y <= current; y++) years.add(y)
  for (const value of selected) {
    const y = Number(value)
    if (Number.isInteger(y) && y > 0) years.add(y)
  }
  return [...years].sort((a, b) => a - b)
}
