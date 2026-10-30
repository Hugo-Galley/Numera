/// <reference types="node" />
// Chaque route appelée par lib/api/<domaine>.ts doit exister côté backend (snapshot OpenAPI tenu à jour par
// le test backend test_openapi_routes.py) : une route supprimée ou renommée côté back casse ce test.
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { recordRequests } from "@/test/recordRequests"

// Vitest tourne depuis frontend/ (npm test, make test-front, CI)
const SNAPSHOT = resolve(process.cwd(), "../backend/tests/snapshots/openapi_routes.json")
const ID = 7

/** « GET /accounts/{account_id} » → « GET /accounts/{} ». */
const normalizeBackend = (route: string) => route.replace(/\{[^}]+\}/g, "{}")
/** « /accounts/7 » → « /accounts/{} » (les identifiants passés valent tous `ID`). */
const normalizeCalled = (method: string, path: string) =>
  `${method} ${path
    .split("/")
    .map((segment) => (segment === String(ID) ? "{}" : segment))
    .join("/")}`

const modules = import.meta.glob<Record<string, unknown>>(["./*.ts", "!./*.test.ts", "!./types.ts"], { eager: true })
// Écarts connus (bugs signalés, non corrigés dans ce lot) : à retirer d'ici quand la route est corrigée.
const KNOWN_MISSING: Record<string, string[]> = {
  "./classement.ts": ["POST /categorization-rules"],
  "./recurring.ts": ["GET /recurring-transactions/{}"],
}

const backendRoutes = new Set((JSON.parse(readFileSync(SNAPSHOT, "utf8")) as string[]).map(normalizeBackend))

describe("lib/api : routes existantes côté backend", () => {
  it("couvre les sept domaines", () => {
    expect(Object.keys(modules).sort()).toEqual(
      ["accounts", "analytics", "classement", "investments", "recurring", "savings", "transactions"].map((d) => `./${d}.ts`),
    )
  })

  it.each(Object.entries(modules))("%s", async (file, module) => {
    const called: string[] = []
    for (const fn of Object.values(module)) {
      const requests = recordRequests()
      // Paramètres obligatoires = identifiants (puis corps) ; la query facultative reste vide
      await (fn as (...args: unknown[]) => Promise<unknown>)(...Array((fn as () => unknown).length).fill(ID))
      called.push(...requests.map((r) => normalizeCalled(r.method, r.path)))
    }

    expect(called.length).toBeGreaterThan(0)
    expect(called.filter((route) => !backendRoutes.has(route))).toEqual(KNOWN_MISSING[file] ?? [])
  })

  it.todo(
    "bug : postCategorizationRules appelle POST /categorization-rules sans « / » final ; le backend ne connaît que " +
      "POST /categorization-rules/ et répond par une redirection 307 vers une adresse sans le préfixe /api derrière nginx " +
      "(création d'une règle depuis le Centre d'Actions, pages/Audit/CreatorModals.tsx)",
  )
  it.todo(
    "bug : getRecurringTransactionsById appelle GET /recurring-transactions/{id}, qui n'existe pas côté backend (405) : " +
      "« Valider » une échéance du calendrier échoue toujours (pages/Calendar/useCalendarData.ts)",
  )
})
