import { accountTypeLabel, categoryTypeLabel } from "./labels"

describe("accountTypeLabel", () => {
  it.each([
    ["courant", "Compte Courant"],
    ["epargne", "Épargne"],
    ["investissement", "Investissement"],
    ["assurance_vie", "Assurance-Vie"],
    ["credit", "Crédit"],
    ["bank", "Compte bancaire"],
  ])("%s → %s", (type, label) => {
    expect(accountTypeLabel(type)).toBe(label)
  })

  it("met une majuscule à un ancien type inconnu, qui reste lisible", () => {
    expect(accountTypeLabel("crypto")).toBe("Crypto")
  })

  it("affiche « Autre » sans type", () => {
    expect(accountTypeLabel(null)).toBe("Autre")
    expect(accountTypeLabel(undefined)).toBe("Autre")
    expect(accountTypeLabel("")).toBe("Autre")
  })
})

describe("categoryTypeLabel", () => {
  it.each([
    ["depense", "Dépense"],
    ["revenu", "Revenu"],
    ["neutre", "Neutre"],
  ])("%s → %s", (type, label) => {
    expect(categoryTypeLabel(type)).toBe(label)
  })

  it("renvoie la valeur brute pour un type inconnu", () => {
    expect(categoryTypeLabel("autre")).toBe("autre")
  })
})
