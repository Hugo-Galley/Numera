import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import i18n from "i18next"
import { appLocale, percentSuffix } from "@/i18n/locale"

export function formatCurrency(
  value: number | null | undefined,
  currencyCode: string = "EUR",
  options: Intl.NumberFormatOptions = {}
) {
  // Un montant qui s'arrondit à zéro (-0, -0,001) s'affiche « 0,00 € », jamais « -0,00 € »
  const safeValue = Number.isFinite(value) && Math.abs(value as number) >= 0.005 ? (value as number) : 0
  try {
    return new Intl.NumberFormat(appLocale(), { style: "currency", currency: currencyCode || "EUR", ...options }).format(safeValue)
  } catch {
    // Code devise invalide (RangeError) : ne jamais faire planter le rendu pour un libellé
    return new Intl.NumberFormat(appLocale(), { style: "currency", currency: "EUR", ...options }).format(safeValue)
  }
}

/** Part de `value` dans `total`, ex. « 12,3 % » (chaîne vide si le total est nul). */
export function formatPercent(value: number, total: number) {
  if (!Number.isFinite(value) || !Number.isFinite(total) || total <= 0) return ""
  const pct = (value / total) * 100
  return `${pct.toLocaleString(appLocale(), { maximumFractionDigits: pct < 10 ? 1 : 0 })}${percentSuffix()}`
}

/** Montant formaté suivi de sa part du total : « 1 234,00 € (12 %) ». */
export function formatAmountWithShare(value: number, total: number, currencyCode: string = "EUR") {
  const amount = formatCurrency(value, currencyCode)
  const share = formatPercent(value, total)
  return share ? `${amount} (${share})` : amount
}

/** Pourcentage à la française : « 12,35 % » (virgule décimale, espace insécable). */
export function formatRate(value: number | null | undefined, digits = 2, withSign = false) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-"
  const text = new Intl.NumberFormat(appLocale(), { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value)
  return `${withSign && value >= 0 ? "+" : ""}${text}${percentSuffix(true)}`
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

const FREQUENCY_KEYS = {
  weekly: "weekly",
  monthly: "monthly",
  quarterly: "quarterly",
  yearly: "yearly",
  annual: "annual",
  "monthly (detected)": "monthlyDetected",
} as const

/** Libellé d'une fréquence renvoyée par l'API (`monthly`, `yearly`…), dans la langue de l'interface. */
export function frequencyLabel(frequency: string): string {
  const key = FREQUENCY_KEYS[frequency as keyof typeof FREQUENCY_KEYS]
  return key ? i18n.t(`frequency.${key}`, { ns: "common" }) : frequency
}


/** Message d'une erreur d'API (ou de repli) : le détail renvoyé par le serveur plutôt qu'un texte générique. */
export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

/** Montant saisi (virgule ou point) → nombre strictement positif, sinon `null`. */
export function parsePositiveAmount(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null
  const n = typeof value === "number" ? value : Number(String(value).replace(",", ".").replace(/\s/g, ""))
  return Number.isFinite(n) && n > 0 ? n : null
}
