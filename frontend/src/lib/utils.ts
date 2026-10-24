import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function formatCurrency(value: number | null | undefined, currencyCode: string = "EUR") {
  const safeValue = Number.isFinite(value) ? (value as number) : 0
  try {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: currencyCode || "EUR" }).format(safeValue)
  } catch {
    // Code devise invalide (RangeError) : ne jamais faire planter le rendu pour un libellé
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(safeValue)
  }
}

/** Part de `value` dans `total`, ex. « 12,3 % » (chaîne vide si le total est nul). */
export function formatPercent(value: number, total: number) {
  if (!Number.isFinite(value) || !Number.isFinite(total) || total <= 0) return ""
  const pct = (value / total) * 100
  return `${pct.toLocaleString("fr-FR", { maximumFractionDigits: pct < 10 ? 1 : 0 })} %`
}

/** Montant formaté suivi de sa part du total : « 1 234,00 € (12 %) ». */
export function formatAmountWithShare(value: number, total: number, currencyCode: string = "EUR") {
  const amount = formatCurrency(value, currencyCode)
  const share = formatPercent(value, total)
  return share ? `${amount} (${share})` : amount
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Échéance du JWT en millisecondes, `null` sans `exp`, `undefined` si le jeton est illisible. */
export function getTokenExpiry(token: string): number | null | undefined {
  try {
    const payloadBase64 = token.split(".")[1]
    if (!payloadBase64) return undefined

    // JWT uses base64url, we need to convert to standard base64 and add padding
    const base64 = payloadBase64.replace(/-/g, '+').replace(/_/g, '/')
    const pad = base64.length % 4
    const padded = pad ? base64 + "=".repeat(4 - pad) : base64

    const payload = JSON.parse(atob(padded))
    return payload.exp ? payload.exp * 1000 : null
  } catch {
    return undefined
  }
}

export function isTokenExpired(token: string | null): boolean {
  if (!token) return true
  const expiry = getTokenExpiry(token)
  if (expiry === undefined) return true
  if (expiry === null) return false
  // Ajouter une marge de 10 secondes pour éviter les problèmes de synchro
  return Date.now() >= expiry - 10000
}

const FREQUENCY_LABELS: Record<string, string> = {
  weekly: "Hebdomadaire",
  monthly: "Mensuelle",
  quarterly: "Trimestrielle",
  yearly: "Annuelle",
  annual: "Annuelle",
  "monthly (detected)": "Mensuelle (détectée)",
}

/** Libellé français d'une fréquence renvoyée par l'API (`monthly`, `yearly`…). */
export function frequencyLabel(frequency: string): string {
  return FREQUENCY_LABELS[frequency] ?? frequency
}
