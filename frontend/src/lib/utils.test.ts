import { ApiError } from "./api"
import {
  errorMessage,
  formatAmountWithShare,
  formatCurrency,
  formatPercent,
  formatRate,
  frequencyLabel,
  getTokenExpiry,
  isTokenExpired,
  parsePositiveAmount,
} from "./utils"
import { makeToken } from "@/test/token"

const NNBSP = " " // séparateur de milliers fr-FR
const NBSP = " " // avant le symbole et le %

describe("formatCurrency", () => {
  it("formate en euros, locale fr-FR (espaces insécables)", () => {
    expect(formatCurrency(1234.5)).toBe(`1${NNBSP}234,50${NBSP}€`)
  })

  it("garde le signe des négatifs", () => {
    expect(formatCurrency(-1234.5)).toBe(`-1${NNBSP}234,50${NBSP}€`)
  })

  it("n'affiche jamais « -0,00 € » pour un montant qui s'arrondit à zéro", () => {
    expect(formatCurrency(-0)).toBe(`0,00${NBSP}€`)
    expect(formatCurrency(-0.001)).toBe(`0,00${NBSP}€`)
    expect(formatCurrency(0.004)).toBe(`0,00${NBSP}€`)
  })

  it("affiche 0 pour null, undefined, NaN et l'infini", () => {
    for (const value of [null, undefined, Number.NaN, Number.POSITIVE_INFINITY]) {
      expect(formatCurrency(value)).toBe(`0,00${NBSP}€`)
    }
  })

  it("formate les autres devises", () => {
    expect(formatCurrency(10, "USD")).toBe(`10,00${NBSP}$US`)
    expect(formatCurrency(10, "GBP")).toBe(`10,00${NBSP}£GB`)
  })

  it("retombe sur l'euro pour un code devise vide ou invalide, sans lever", () => {
    expect(formatCurrency(10, "")).toBe(`10,00${NBSP}€`)
    expect(formatCurrency(10, "PAS-UNE-DEVISE")).toBe(`10,00${NBSP}€`)
  })

  it("transmet les options Intl", () => {
    expect(formatCurrency(1234.56, "EUR", { maximumFractionDigits: 0, minimumFractionDigits: 0 })).toBe(
      `1${NNBSP}235${NBSP}€`,
    )
  })
})

describe("formatPercent", () => {
  it("affiche une décimale sous 10 %, aucune au-delà", () => {
    expect(formatPercent(1, 30)).toBe("3,3 %")
    expect(formatPercent(1, 8)).toBe("13 %")
    expect(formatPercent(50, 50)).toBe("100 %")
  })

  it("renvoie une chaîne vide si le total est nul, négatif ou non fini", () => {
    expect(formatPercent(10, 0)).toBe("")
    expect(formatPercent(10, -5)).toBe("")
    expect(formatPercent(Number.NaN, 10)).toBe("")
    expect(formatPercent(10, Number.POSITIVE_INFINITY)).toBe("")
  })
})

describe("formatAmountWithShare", () => {
  it("ajoute la part du total entre parenthèses", () => {
    expect(formatAmountWithShare(25, 100)).toBe(`25,00${NBSP}€ (25 %)`)
  })

  it("n'affiche que le montant si le total est à 0", () => {
    expect(formatAmountWithShare(25, 0)).toBe(`25,00${NBSP}€`)
  })

  it("respecte la devise", () => {
    expect(formatAmountWithShare(5, 100, "USD")).toBe(`5,00${NBSP}$US (5 %)`)
  })
})

describe("formatRate", () => {
  it("formate à la française avec deux décimales par défaut", () => {
    expect(formatRate(12.345)).toBe(`12,35${NBSP}%`)
    expect(formatRate(-3.1)).toBe(`-3,10${NBSP}%`)
  })

  it("respecte le nombre de décimales demandé", () => {
    expect(formatRate(1234.5, 0)).toBe(`1${NNBSP}235${NBSP}%`)
  })

  it("préfixe « + » sur demande, pour zéro et les positifs seulement", () => {
    expect(formatRate(4.2, 1, true)).toBe(`+4,2${NBSP}%`)
    expect(formatRate(0, 1, true)).toBe(`+0,0${NBSP}%`)
    expect(formatRate(-4.2, 1, true)).toBe(`-4,2${NBSP}%`)
  })

  it("affiche « - » pour null, undefined ou une valeur non finie", () => {
    expect(formatRate(null)).toBe("-")
    expect(formatRate(undefined)).toBe("-")
    expect(formatRate(Number.NaN)).toBe("-")
  })
})

describe("getTokenExpiry / isTokenExpired", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] })
    vi.setSystemTime(new Date("2026-10-30T12:00:00Z"))
  })
  afterEach(() => vi.useRealTimers())

  const withPayload = (payload: object) => `x.${btoa(JSON.stringify(payload))}.sig`

  it("lit l'échéance d'un jeton base64url, en millisecondes", () => {
    const exp = Math.floor(Date.now() / 1000) + 3600
    expect(getTokenExpiry(makeToken({ expInMinutes: 60 }))).toBe(exp * 1000)
  })

  it("décode les caractères base64url (- et _) et le padding manquant", () => {
    // « ??? » encode en « Pz8/ » (base64) donc « Pz8_ » (base64url)
    const payload = btoa(JSON.stringify({ exp: 2000000000, s: "???" })).replace(/\//g, "_").replace(/=+$/, "")
    expect(getTokenExpiry(`x.${payload}.sig`)).toBe(2000000000 * 1000)
  })

  it("renvoie null pour un jeton sans exp, undefined pour un jeton illisible", () => {
    expect(getTokenExpiry(withPayload({ sub: "admin" }))).toBeNull()
    expect(getTokenExpiry("pas-un-jwt")).toBeUndefined()
    expect(getTokenExpiry("x.%%%.sig")).toBeUndefined()
    expect(getTokenExpiry(`x.${btoa("pas du json")}.sig`)).toBeUndefined()
  })

  it("considère expirés un jeton absent, illisible ou passé", () => {
    expect(isTokenExpired(null)).toBe(true)
    expect(isTokenExpired("")).toBe(true)
    expect(isTokenExpired("pas-un-jwt")).toBe(true)
    expect(isTokenExpired(makeToken({ expInMinutes: -1 }))).toBe(true)
  })

  it("garde une marge de 10 secondes avant l'échéance", () => {
    expect(isTokenExpired(makeToken({ expInMinutes: 5 / 60 }))).toBe(true)
    expect(isTokenExpired(makeToken({ expInMinutes: 15 / 60 }))).toBe(false)
  })

  it("considère valide un jeton sans exp", () => {
    expect(isTokenExpired(withPayload({ sub: "admin" }))).toBe(false)
  })
})

describe("parsePositiveAmount", () => {
  it("accepte la virgule ou le point décimal et les espaces", () => {
    expect(parsePositiveAmount("12,50")).toBe(12.5)
    expect(parsePositiveAmount("12.50")).toBe(12.5)
    expect(parsePositiveAmount("1 234,5")).toBe(1234.5)
    expect(parsePositiveAmount(`1${NNBSP}234`)).toBe(1234)
    expect(parsePositiveAmount(42)).toBe(42)
  })

  it("refuse le vide, zéro, les négatifs et le texte", () => {
    for (const value of [null, undefined, "", "0", 0, "-5", -5, "abc", "12€", Number.NaN]) {
      expect(parsePositiveAmount(value)).toBeNull()
    }
  })
})

describe("errorMessage", () => {
  it("reprend le message d'une ApiError à detail texte", () => {
    expect(errorMessage(new ApiError(400, "Compte introuvable", "Compte introuvable"), "Erreur")).toBe(
      "Compte introuvable",
    )
  })

  it("reprend le message d'une ApiError à detail structuré", () => {
    const detail = { code: "duplicate", message: "Doublon détecté", context: { id: 3 } }
    expect(errorMessage(new ApiError(409, "Doublon détecté", detail), "Erreur")).toBe("Doublon détecté")
  })

  it("reprend le message d'une Error ordinaire", () => {
    expect(errorMessage(new Error("Réseau indisponible"), "Erreur")).toBe("Réseau indisponible")
  })

  it("retombe sur le repli pour un message vide ou une valeur inconnue", () => {
    expect(errorMessage(new Error(""), "Erreur")).toBe("Erreur")
    expect(errorMessage("texte", "Erreur")).toBe("Erreur")
    expect(errorMessage(null, "Erreur")).toBe("Erreur")
    expect(errorMessage({ message: "objet" }, "Erreur")).toBe("Erreur")
  })
})

describe("frequencyLabel", () => {
  it.each([
    ["weekly", "Hebdomadaire"],
    ["monthly", "Mensuelle"],
    ["quarterly", "Trimestrielle"],
    ["yearly", "Annuelle"],
    ["annual", "Annuelle"],
    ["monthly (detected)", "Mensuelle (détectée)"],
  ])("%s → %s", (frequency, label) => {
    expect(frequencyLabel(frequency)).toBe(label)
  })

  it("renvoie la valeur brute pour une fréquence inconnue", () => {
    expect(frequencyLabel("biweekly")).toBe("biweekly")
  })
})
