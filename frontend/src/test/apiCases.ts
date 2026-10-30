/** Table de cas pour un module `lib/api/<domaine>.ts` : chaque fonction exportée → méthode, chemin, query, corps reçus par MSW. */
import { recordRequests } from "./recordRequests"

export interface ApiCase {
  /** Nom de la fonction exportée. */
  fn: string
  args?: unknown[]
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
  path: string
  /** Query attendue, `?` compris (vide par défaut). */
  query?: string
  /** Corps JSON attendu (absent par défaut). */
  body?: unknown
  /** Envoi multipart (`api.upload`) : corps non JSON, pas vérifié ici (voir `lib/api.test.ts`). */
  upload?: boolean
}

type ApiModule = Record<string, unknown>

/** Un test par cas, plus un test qui exige un cas pour chaque fonction exportée du module. */
export function describeApiCases(name: string, module: ApiModule, cases: ApiCase[]) {
  describe(`lib/api/${name}`, () => {
    it("chaque fonction exportée a son cas", () => {
      expect(cases.map((c) => c.fn).sort()).toEqual(Object.keys(module).sort())
    })

    it.each(cases.map((c) => [`${c.fn} → ${c.method} ${c.path}${c.query ?? ""}`, c] as const))("%s", async (_label, c) => {
      const requests = recordRequests()
      const fn = module[c.fn] as (...args: unknown[]) => Promise<unknown>

      await fn(...(c.args ?? []))

      expect(requests).toHaveLength(1)
      const [request] = requests
      expect({ method: request.method, path: request.path, query: request.search }).toEqual({
        method: c.method,
        path: c.path,
        query: c.query ?? "",
      })
      if (c.upload) expect(request.headers.get("content-type")).not.toBe("application/json")
      else expect(request.body === null ? undefined : JSON.parse(request.body)).toEqual(c.body)
    })
  })
}

/** Corps type envoyé aux fonctions qui en prennent un. */
export const BODY = { name: "test", amount: 12.5 }
