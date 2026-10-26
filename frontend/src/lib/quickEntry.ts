/** Saisie rapide de l'Omnibox : « 12,50 boulangerie » → dépense, « +1200 prime » → revenu. */
export interface QuickEntry {
  amount: number
  type: "Sortie" | "Entree"
  merchant: string
}

const QUICK_ENTRY = /^([+-]?)\s*(\d+(?:[.,]\d{1,2})?)\s*€?(?:\s+(.+))?$/

export function parseQuickEntry(query: string): QuickEntry | null {
  const match = QUICK_ENTRY.exec(query.trim())
  if (!match) return null
  const amount = Number(match[2].replace(",", "."))
  if (!(amount > 0)) return null
  return { amount, type: match[1] === "+" ? "Entree" : "Sortie", merchant: (match[3] ?? "").trim() }
}
