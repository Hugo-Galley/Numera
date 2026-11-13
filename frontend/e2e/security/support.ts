import { createHmac } from "node:crypto"
import { expect, type APIRequestContext, type Page } from "@playwright/test"

export const CREDENTIALS = { username: "e2e", password: "e2e-security-pass" }
export const SECURITY_STATE = "e2e/.auth/security.json"
export const API = "http://localhost:8102"
export const MOCK = "http://127.0.0.1:8103"
export const BACKUP_KEY = Buffer.from("e2e-security-backup-key-32bytes!").toString("base64url") + "=" // = clé de backend-security.sh
export const EMPTY_STATE = { cookies: [], origins: [] }

const B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

/** Code TOTP (RFC 6238 : SHA-1, 6 chiffres, pas de 30 s) du pas courant décalé de `offset` pas. */
export function totpCode(secret: string, offset = 0, now = Date.now()): string {
  let bits = ""
  for (const c of secret.replace(/[\s=]/g, "").toUpperCase()) bits += B32.indexOf(c).toString(2).padStart(5, "0")
  const key = Buffer.from(bits.match(/.{8}/g)!.map((b) => parseInt(b, 2)))
  const counter = Buffer.alloc(8)
  counter.writeBigUInt64BE(BigInt(Math.floor(now / 30_000) + offset))
  const digest = createHmac("sha1", key).update(counter).digest()
  const o = digest[digest.length - 1] & 0x0f
  return String((digest.readUInt32BE(o) & 0x7fffffff) % 1_000_000).padStart(6, "0")
}

/** Jeton de session par l'API (avant activation de la 2FA). */
export async function apiToken(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${API}/auth/token`, { form: CREDENTIALS })
  expect(res.ok()).toBeTruthy()
  return (await res.json()).access_token
}

/** Journal du faux serveur externe (ntfy et CONNECT refusés). */
export async function mockLog(request: APIRequestContext): Promise<Array<Record<string, unknown>>> {
  return (await request.get(`${MOCK}/__requests`)).json()
}

export async function openSecurity(page: Page, tab: "security" | "data" | "notifications" = "security") {
  await page.goto(`/settings?tab=${tab}`)
  await expect(page.getByRole("tab", { selected: true })).toBeVisible()
}
