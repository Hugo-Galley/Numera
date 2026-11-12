/** Garde-fou : tous les tests vivent sous src/test/ (au chemin miroir de leur source), jamais à côté du code. */
const tests = Object.keys(import.meta.glob("/src/**/*.test.{ts,tsx}"))

describe("rangement des tests", () => {
  it("trouve bien les tests (le garde-fou ne passe pas à vide)", () => {
    expect(tests.length).toBeGreaterThan(50)
  })

  it("aucun *.test.ts(x) en dehors de src/test/", () => {
    expect(tests.filter((path) => !path.startsWith("/src/test/"))).toEqual([])
  })
})
