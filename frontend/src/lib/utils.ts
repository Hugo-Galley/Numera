import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function formatCurrency(value: number | null | undefined, currencyCode: string = "EUR") {
  const safeValue = value || 0
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: currencyCode }).format(safeValue)
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isTokenExpired(token: string | null): boolean {
  if (!token) return true
  try {
    const payloadBase64 = token.split(".")[1]
    if (!payloadBase64) return true
    
    // JWT uses base64url, we need to convert to standard base64 and add padding
    const base64 = payloadBase64.replace(/-/g, '+').replace(/_/g, '/')
    const pad = base64.length % 4
    const padded = pad ? base64 + "=".repeat(4 - pad) : base64
    
    const decodedJson = atob(padded)
    const payload = JSON.parse(decodedJson)
    const exp = payload.exp
    if (!exp) return false
    // Ajouter une marge de 10 secondes pour éviter les problèmes de synchro
    return Date.now() >= (exp * 1000) - 10000
  } catch {
    return true
  }
}
