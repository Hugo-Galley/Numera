import { looksSensitive } from "./privacyScanner"

// Le scanner DOM (`startPrivacyScanner`) relève du lot 3 ; ici, seulement la détection de texte.
describe("looksSensitive", () => {
  describe("détecte les montants", () => {
    it.each([
      "1 234,56 €",
      "1 234,50 €", // sortie réelle de formatCurrency
      "12 €",
      "10 000 €",
      "€ 0",
      "$ 45",
      "EUR 100",
      "3k€",
      "Solde : 2,5M€",
    ])("avec devise : « %s »", (text) => {
      expect(looksSensitive(text)).toBe(true)
    })

    it.each(["1 234", "1 234", "1 234 567", "2 500", "1.234,56", "1,234"])(
      "avec séparateur de milliers : « %s »",
      (text) => {
        expect(looksSensitive(text)).toBe(true)
      },
    )

    it.each(["12,50", "12.50", "100,00", "Reste 45,90 ce mois-ci"])("avec deux décimales : « %s »", (text) => {
      expect(looksSensitive(text)).toBe(true)
    })
  })

  describe("ignore ce qui n'est pas un montant", () => {
    it.each(["22/10/2026", "2026-10-30", "30 oct. 2026", "12:30"])("date ou heure : « %s »", (text) => {
      expect(looksSensitive(text)).toBe(false)
    })

    it.each(["2026", "Année 2025"])("année : « %s »", (text) => {
      expect(looksSensitive(text)).toBe(false)
    })

    it.each(["12 %", "12,5 %", "+4,2 %"])("pourcentage à une décimale au plus : « %s »", (text) => {
      expect(looksSensitive(text)).toBe(false)
    })

    it.each(["v1.2.3", "1.5", "0,5", "5 transactions", "Mois 10", "Page 1 / 12", "Score 85/100", "Tél. 06 12 34 56 78", "ISIN FR0010315770"])(
      "numéro ou compteur : « %s »",
      (text) => {
        expect(looksSensitive(text)).toBe(false)
      },
    )

    it("texte vide, sans chiffre ou trop long (plus de 200 caractères)", () => {
      expect(looksSensitive(null)).toBe(false)
      expect(looksSensitive(undefined)).toBe(false)
      expect(looksSensitive("")).toBe(false)
      expect(looksSensitive("Dépenses du mois €")).toBe(false)
      expect(looksSensitive(`${"x".repeat(200)} 12 €`)).toBe(false)
    })
  })

    it.each(["22.10.2026", "Le 01.02.2025", "1.2.3456"])("date ou version à points : « %s »", (text) => {
      expect(looksSensitive(text)).toBe(false)
    })

    it.each(["3,14 %", "12,34 %", "-0,50 %", "3,14 %", "Taux 2.25%"])("pourcentage à deux décimales : « %s »", (text) => {
      expect(looksSensitive(text)).toBe(false)
    })
  })

  it("détecte toujours un montant voisin d'un pourcentage ou d'une date", () => {
    expect(looksSensitive("45,90 soit 3,14 %")).toBe(true)
    expect(looksSensitive("Le 22.10.2026 : 1 234,56")).toBe(true)
})
