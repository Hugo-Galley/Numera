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

  // Bug suspect, à trancher : « 1 234 loyer » donne aujourd'hui { amount: 1, merchant: "234 loyer" }
  // (le séparateur de milliers est pris pour la fin du montant), une dépense de 1 € créée sans alerte.
  it.todo("refuse ou lit 1234 pour un montant avec séparateur de milliers (« 1 234 loyer »)")
})
