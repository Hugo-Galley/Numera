import { execFileSync } from "node:child_process"
import { mkdtempSync, readdirSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { test, expect } from "../fixtures"
import { API, BACKEND_DIR, BACKUP_KEY, apiToken, backendPython, openSecurity } from "./support"

test("sauvegarde : lancement depuis Paramètres → Données, état affiché, fichier chiffré restaurable", async ({ page, request }) => {
  const headers = { Authorization: `Bearer ${await apiToken(request)}` }
  const before: number = (await (await request.get(`${API}/admin/backup/status`, { headers })).json()).backup_count
  await openSecurity(page, "data")

  await page.getByRole("button", { name: "Sauvegarder maintenant" }).click()
  const done = page.getByRole("dialog")
  await expect(done.getByText("Sauvegarde terminée")).toBeVisible()
  await done.getByRole("button", { name: "Fermer" }).click()

  const row = (label: string) => page.getByText(label, { exact: true }).locator("xpath=..")
  await expect(row("Sauvegardes conservées sur le serveur")).toContainText(String(before + 1))
  await expect(row("Chiffrement")).toContainText("Chiffrée")

  const status = await (await request.get(`${API}/admin/backup/status`, { headers })).json()
  expect(status).toMatchObject({ configured: true, encrypted: true, backup_count: before + 1, stale: false, last_error: null })

  // Restauration (scripts/restore.py, pas d'écran dédié) : la sauvegarde chiffrée se relit dans une base temporaire
  const dir = join(BACKEND_DIR, "data", "e2e-security-backups")
  const file = readdirSync(dir).filter((f) => f.endsWith(".enc")).sort().pop()
  expect(file, "fichier .enc dans BACKUP_DIR").toBeTruthy()
  const dest = join(mkdtempSync(join(tmpdir(), "numera-restore-")), "restored.db")
  const python = backendPython()
  execFileSync(python, ["scripts/restore.py", join(dir, file!), "--dest", dest, "--key", BACKUP_KEY], { cwd: BACKEND_DIR })
  const tables = execFileSync(python, ["-c", "import sqlite3,sys;print(sqlite3.connect(sys.argv[1]).execute(\"select count(*) from sqlite_master where name='accounts'\").fetchone()[0])", dest])
  expect(tables.toString().trim()).toBe("1")
})
