import { formatCurrency } from "./utils"

describe("formatCurrency", () => {
  it("formate en euros, locale fr-FR (espaces insécables)", () => {
    expect(formatCurrency(1234.5)).toBe("1\u202f234,50\u00a0€")
  })
})
