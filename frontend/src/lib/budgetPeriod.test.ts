import { formatPeriodRange, type BudgetPeriod } from "./budgetPeriod"

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
