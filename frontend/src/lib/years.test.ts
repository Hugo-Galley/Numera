import { afterEach, beforeEach } from "vitest"
import { yearOptions } from "./years"

describe("yearOptions", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] })
    vi.setSystemTime(new Date(2027, 0, 5))
  })
  afterEach(() => vi.useRealTimers())

  it("va de la première année utile à l'année courante, 2027 comprise", () => {
    const years = yearOptions()
    expect(years[0]).toBe(2020)
    expect(years[years.length - 1]).toBe(2027)
  })

  it("inclut toujours les valeurs sélectionnées, même hors plage", () => {
    const years = yearOptions("2018", "2029")
    expect(years).toContain(2018)
    expect(years).toContain(2029)
    expect(years).toEqual([...years].sort((a, b) => a - b))
  })

  it("ignore une valeur non numérique", () => {
    expect(yearOptions("", "abc")).toEqual(yearOptions())
  })
})
