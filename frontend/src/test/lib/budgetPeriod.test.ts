import { formatPeriodRange, periodProgress, type BudgetPeriod } from "@/lib/budgetPeriod"

const period = (overrides: Partial<BudgetPeriod> = {}): BudgetPeriod => ({
  year: 2026,
  month: 9,
  mode: "salary",
  start: "2026-08-25",
  end: "2026-09-25",
  current: { year: 2026, month: 10 },
  ...overrides,
})

describe("formatPeriodRange", () => {
  it("affiche la fenêtre du mois budgétaire en mode paie", () => {
    expect(formatPeriodRange(period())).toBe("25 août → 25 sept.")
  })

  it("lit les dates en heure locale, sans décalage de jour", () => {
    expect(formatPeriodRange(period({ start: "2026-12-31", end: "2027-01-01" }))).toBe("31 déc. → 1 janv.")
  })

  it("ne renvoie rien en mode civil ou sans période", () => {
    expect(formatPeriodRange(period({ mode: "civil" }))).toBeNull()
    expect(formatPeriodRange(null)).toBeNull()
  })
})

describe("periodProgress", () => {
  const november = period({ start: "2026-11-01", end: "2026-11-30" })

  it("donne le jour courant et la durée (fin incluse) quand aujourd'hui est dans la période", () => {
    expect(periodProgress(november, new Date(2026, 10, 23, 18, 30))).toEqual({ day: 23, total: 30 })
    expect(periodProgress(november, new Date(2026, 10, 1))).toEqual({ day: 1, total: 30 })
    expect(periodProgress(november, new Date(2026, 10, 30, 23, 59))).toEqual({ day: 30, total: 30 })
  })

  it("ne renvoie rien pour une période passée, à venir ou absente", () => {
    expect(periodProgress(november, new Date(2026, 11, 1))).toBeNull()
    expect(periodProgress(november, new Date(2026, 9, 31))).toBeNull()
    expect(periodProgress(null, new Date(2026, 10, 23))).toBeNull()
  })

  it("compte les jours civils, même au passage à l'heure d'hiver", () => {
    const october = period({ start: "2026-10-01", end: "2026-10-31" })
    expect(periodProgress(october, new Date(2026, 9, 31, 12))).toEqual({ day: 31, total: 31 })
  })
})
