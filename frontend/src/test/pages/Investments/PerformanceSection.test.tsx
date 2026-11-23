/** Investissements : graduations de l'axe des montants, compactes pour ne jamais être coupées. */
import { formatCompactCurrency } from "@/lib/utils"

describe("Investissements : format compact des axes", () => {
  it("abrège les milliers (« 14 k € », « 10,5 k € »)", () => {
    expect(formatCompactCurrency(14000).replace(/\s/g, " ")).toBe("14 k €")
    expect(formatCompactCurrency(10500).replace(/\s/g, " ")).toBe("10,5 k €")
  })

  it("garde les petits montants entiers", () => {
    expect(formatCompactCurrency(0).replace(/\s/g, " ")).toBe("0 €")
    expect(formatCompactCurrency(750).replace(/\s/g, " ")).toBe("750 €")
  })
})
