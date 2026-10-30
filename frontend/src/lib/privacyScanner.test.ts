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

  // Faux positifs actuels, à trancher (le commentaire du code annonce exclure « 22.10.2026 ») :
  // « 22.10.2026 » est masqué via le motif des milliers (« 10.202 ») ; « 3,14 % » et « 12,34 % »
  // le sont via le motif des décimales.
  it.todo("ne masque pas une date à points (« 22.10.2026 »)")
  it.todo("ne masque pas un pourcentage à deux décimales (« 3,14 % »)")
})
