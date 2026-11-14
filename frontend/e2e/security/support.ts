import { execFileSync } from "node:child_process"
import { createHmac } from "node:crypto"
import { existsSync } from "node:fs"
import { join, resolve } from "node:path"
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

/** Dossier `backend/` (les tests tournent depuis `frontend/`). */
export const BACKEND_DIR = resolve(process.cwd(), "../backend")
export const DB_FILE = join(BACKEND_DIR, "data", "e2e-security.db")

/** Python du backend, toujours en chemin absolu : `E2E_PYTHON` est relatif à `backend/` (CI : `.venv/bin/python`). */
export function backendPython(): string {
  const wanted = process.env.E2E_PYTHON
  if (wanted) return resolve(BACKEND_DIR, wanted)
  const venv = join(BACKEND_DIR, ".venv/bin/python")
  return existsSync(venv) ? venv : "python3"
}

/**
 * Remet la 2FA à zéro quel que soit l'état laissé par une tentative précédente (échec, retry, worker tué) : efface ses
 * réglages dans la base jetable. Chaque test repart ainsi d'un compte sans second facteur, sans dépendre de l'ordre.
 */
export function resetTwoFactor(): void {
  const sql = "delete from system_settings where key in ('totp_secret','totp_pending_secret','totp_last_step','totp_recovery_codes')"
  execFileSync(backendPython(), ["-c", "import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute(sys.argv[2]);c.commit()", DB_FILE, sql])
}

/** Active la 2FA par l'API (le scénario n'a pas à passer par l'écran) ; `activatedAt` = instant du code consommé. */
export async function enableTwoFactor(request: APIRequestContext) {
  const headers = { Authorization: `Bearer ${await apiToken(request)}` }
  const setup = await request.post(`${API}/auth/totp/setup`, { headers, data: { current_password: CREDENTIALS.password } })
  expect(setup.ok()).toBeTruthy()
  const secret: string = (await setup.json()).secret
  const activatedAt = Date.now()
  const enable = await request.post(`${API}/auth/totp/enable`, { headers, data: { code: totpCode(secret, 0, activatedAt) } })
  expect(enable.ok()).toBeTruthy()
  const recovery: string[] = (await enable.json()).recovery_codes
  return { secret, recovery, activatedAt }
}
