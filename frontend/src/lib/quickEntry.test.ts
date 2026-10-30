import { parseQuickEntry } from "./quickEntry"

describe("parseQuickEntry", () => {
  it("lit un montant seul comme une dépense sans libellé", () => {
    expect(parseQuickEntry("12")).toEqual({ amount: 12, type: "Sortie", merchant: "" })
  })

  it("lit un montant suivi d'un libellé", () => {
    expect(parseQuickEntry("12,50 boulangerie")).toEqual({ amount: 12.5, type: "Sortie", merchant: "boulangerie" })
    expect(parseQuickEntry("8.2 café du coin")).toEqual({ amount: 8.2, type: "Sortie", merchant: "café du coin" })
  })

  it("accepte le symbole euro et des espaces autour", () => {
    expect(parseQuickEntry("  12,50€ boulangerie  ")).toEqual({ amount: 12.5, type: "Sortie", merchant: "boulangerie" })
    expect(parseQuickEntry("12 € boulangerie")).toEqual({ amount: 12, type: "Sortie", merchant: "boulangerie" })
  })

  it("« + » donne un revenu, « - » une dépense, montant toujours positif", () => {
    expect(parseQuickEntry("+1200 prime")).toEqual({ amount: 1200, type: "Entree", merchant: "prime" })
    expect(parseQuickEntry("+ 1200 prime")).toEqual({ amount: 1200, type: "Entree", merchant: "prime" })
    expect(parseQuickEntry("-30 essence")).toEqual({ amount: 30, type: "Sortie", merchant: "essence" })
  })

  it.each([
    "",
    "   ",
    "boulangerie",
    "boulangerie 12",
    "0",
    "0,00 rien",
    "12,505 trop de décimales",
    "12abc",
    "++12",
  ])("refuse « %s »", (query) => {
    expect(parseQuickEntry(query)).toBeNull()
  })

  it("lit un montant avec séparateur de milliers (espace, insécable ou fine)", () => {
    expect(parseQuickEntry("1 234 loyer")).toEqual({ amount: 1234, type: "Sortie", merchant: "loyer" })
    expect(parseQuickEntry("1 234,50 € loyer")).toEqual({ amount: 1234.5, type: "Sortie", merchant: "loyer" })
    expect(parseQuickEntry("+12 500 prime")).toEqual({ amount: 12500, type: "Entree", merchant: "prime" })
    expect(parseQuickEntry("1 234 567")).toEqual({ amount: 1234567, type: "Sortie", merchant: "" })
  })

  it("garde un petit nombre suivi d'un libellé qui commence par un chiffre court", () => {
    expect(parseQuickEntry("2 croissants")).toEqual({ amount: 2, type: "Sortie", merchant: "croissants" })
    expect(parseQuickEntry("3 12 cafés")).toEqual({ amount: 3, type: "Sortie", merchant: "12 cafés" })
  })
})
