/** JWT de test (non signé, lisible par `getTokenExpiry` / `isTokenExpired`). */
function base64url(value: object): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "")
}

interface TokenOptions {
  /** Minutes avant expiration (négatif = déjà expiré). 60 par défaut : au-delà de la marge de renouvellement. */
  expInMinutes?: number
  sub?: string
}

export function makeToken({ expInMinutes = 60, sub = "admin" }: TokenOptions = {}): string {
  const exp = Math.floor(Date.now() / 1000) + Math.round(expInMinutes * 60)
  return `${base64url({ alg: "HS256", typ: "JWT" })}.${base64url({ sub, exp })}.signature`
}
