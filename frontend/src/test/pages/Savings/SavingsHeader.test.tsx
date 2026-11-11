/** En-tête Épargne : le sélecteur d'année suivant la date du jour (audit F-01). */
import { render, screen } from "@testing-library/react"
import { afterEach, beforeEach } from "vitest"
import { SavingsHeader } from "@/pages/Savings/SavingsHeader"
import type { SavingsCtx } from "@/pages/Savings/useSavings"

describe("SavingsHeader", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] })
    vi.setSystemTime(new Date(2027, 0, 5))
  })
  afterEach(() => vi.useRealTimers())

  it("affiche l'année 2027 sélectionnée en janvier 2027", () => {
    const ctx = { month: "1", months: ["Janvier"], period: "monthly", year: "2027", setMonth: vi.fn(), setPeriod: vi.fn(), setYear: vi.fn() } as unknown as SavingsCtx
    render(<SavingsHeader ctx={ctx} />)
    expect(screen.getAllByRole("combobox").map((t) => t.textContent)).toContain("2027")
  })
})
