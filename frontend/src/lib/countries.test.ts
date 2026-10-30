import { COUNTRIES } from "./countries"

describe("COUNTRIES", () => {
  it("a des codes et des noms uniques", () => {
    expect(new Set(COUNTRIES.map((c) => c.code)).size).toBe(COUNTRIES.length)
    expect(new Set(COUNTRIES.map((c) => c.name)).size).toBe(COUNTRIES.length)
  })

  it("utilise des codes ISO 3166 alpha-3, plus « WORLD » pour les ETF monde", () => {
    for (const { code } of COUNTRIES) {
      expect(code === "WORLD" || /^[A-Z]{3}$/.test(code)).toBe(true)
    }
    expect(COUNTRIES.find((c) => c.code === "WORLD")?.name).toBe("Monde (ETF World)")
  })

  it("commence par la France", () => {
    expect(COUNTRIES[0]).toEqual({ name: "France", code: "FRA" })
  })
})
