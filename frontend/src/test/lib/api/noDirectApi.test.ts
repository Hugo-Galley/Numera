/** Garde-fou : les écrans passent par les fonctions de lib/api/<domaine>.ts, jamais par `api.get(...)` & co. directement. */
const sources = import.meta.glob<string>("/src/**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true })

const DIRECT_CALL = /\bapi\s*\.\s*(get|post|put|patch|delete|upload|download)\b/

describe("appels API", () => {
  it("le garde-fou lit bien les sources", () => {
    expect(Object.keys(sources).length).toBeGreaterThan(200)
  })

  it("aucun appel direct à api.* hors de lib/api/ et lib/api.ts", () => {
    const offenders = Object.entries(sources)
      .filter(([path]) => !path.startsWith("/src/test/") && !path.startsWith("/src/lib/api/") && path !== "/src/lib/api.ts")
      .filter(([, code]) => DIRECT_CALL.test(code))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })
})
