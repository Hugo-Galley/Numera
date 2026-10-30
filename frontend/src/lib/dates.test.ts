import { endOfDayParam, nowLocalInput, startOfDayParam, toInputValue, toNaiveLocal, todayLocal } from "./dates"

// TZ=Europe/Paris (vitest.config.ts) : UTC+2 en été, UTC+1 en hiver.

describe("toInputValue", () => {
  it("garde l'heure du mur d'un datetime naïf, sans conversion UTC", () => {
    expect(toInputValue("2026-08-15T23:30:00")).toBe("2026-08-15T23:30")
    expect(toInputValue("2026-08-15T23:30:45.123")).toBe("2026-08-15T23:30")
  })

  it("complète une date seule à minuit", () => {
    expect(toInputValue("2026-01-31")).toBe("2026-01-31T00:00")
  })

  it("convertit en heure locale une date avec fuseau", () => {
    expect(toInputValue("2026-08-15T22:30:00Z")).toBe("2026-08-16T00:30")
    expect(toInputValue("2026-01-15T10:00:00+01:00")).toBe("2026-01-15T10:00")
  })

  it("renvoie une chaîne vide pour une valeur absente ou illisible", () => {
    expect(toInputValue(null)).toBe("")
    expect(toInputValue(undefined)).toBe("")
    expect(toInputValue("")).toBe("")
    expect(toInputValue("n'importe quoi Z")).toBe("")
  })
})

describe("toNaiveLocal", () => {
  it("ajoute les secondes à une valeur datetime-local, sans Z", () => {
    expect(toNaiveLocal("2026-08-15T23:30")).toBe("2026-08-15T23:30:00")
  })

  it("complète une date seule à minuit", () => {
    expect(toNaiveLocal("2026-12-31")).toBe("2026-12-31T00:00:00")
  })

  it("tronque les millisecondes d'un datetime naïf", () => {
    expect(toNaiveLocal("2026-08-15T23:30:45.999")).toBe("2026-08-15T23:30:45")
  })

  it("convertit en heure locale naïve une date avec fuseau", () => {
    expect(toNaiveLocal("2026-12-31T23:30:00Z")).toBe("2027-01-01T00:30:00")
  })
})

describe("aller-retour API → champ → API", () => {
  it.each([
    "2026-08-15T23:30:00", // 23 h 30 en été : toISOString() aurait changé le jour
    "2026-12-31T23:59:00", // dernier jour de l'année
    "2026-03-29T02:30:00", // heure inexistante (passage à l'heure d'été) : gardée telle quelle
    "2026-01-01T00:00:00",
  ])("%s ne bouge pas", (value) => {
    expect(toNaiveLocal(toInputValue(value))).toBe(value)
  })

  it("une date seule revient à minuit le même jour", () => {
    expect(toNaiveLocal(toInputValue("2026-10-31"))).toBe("2026-10-31T00:00:00")
  })
})

describe("startOfDayParam / endOfDayParam", () => {
  it("bornent la journée choisie, dernier jour inclus", () => {
    expect(startOfDayParam("2026-10-01")).toBe("2026-10-01T00:00:00")
    expect(endOfDayParam("2026-10-31")).toBe("2026-10-31T23:59:59")
  })

  it("ignorent l'heure d'une valeur datetime", () => {
    expect(startOfDayParam("2026-10-01T15:42")).toBe("2026-10-01T00:00:00")
    expect(endOfDayParam("2026-10-31T08:00:00")).toBe("2026-10-31T23:59:59")
  })
})

describe("todayLocal / nowLocalInput", () => {
  beforeEach(() => vi.useFakeTimers({ toFake: ["Date"] }))
  afterEach(() => vi.useRealTimers())

  it("donne le jour local juste après minuit, alors qu'il est encore la veille en UTC", () => {
    vi.setSystemTime(new Date("2026-10-30T23:30:00Z")) // 31 oct. 00 h 30 à Paris (UTC+1, heure d'hiver)
    expect(todayLocal()).toBe("2026-10-31")
    expect(nowLocalInput()).toBe("2026-10-31T00:30")
  })

  it("donne le jour local juste avant minuit, un soir d'été", () => {
    vi.setSystemTime(new Date("2026-08-15T21:59:00Z")) // 15 août 23 h 59 à Paris (UTC+2)
    expect(todayLocal()).toBe("2026-08-15")
    expect(nowLocalInput()).toBe("2026-08-15T23:59")
  })

  it("passe à l'année suivante à minuit le 31 décembre", () => {
    vi.setSystemTime(new Date("2026-12-31T23:00:00Z")) // 1er janv. 2027 00 h 00 à Paris
    expect(todayLocal()).toBe("2027-01-01")
  })
})
