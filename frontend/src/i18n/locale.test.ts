import { i18n, setLanguage } from "@/i18n"
import { appLocale, dateLocale, monthName, percentSuffix } from "@/i18n/locale"
import { formatCurrency, formatPercent, formatRate, frequencyLabel } from "@/lib/utils"
import { safeStorage } from "@/lib/storage"

const norm = (text: string) => text.replace(/[  ]/g, " ")

describe("langue de l'interface et formats", () => {
  afterEach(() => setLanguage("fr"))

  it("suit le français par défaut (montants, pourcentages, mois, fréquences)", () => {
    expect(appLocale()).toBe("fr-FR")
    expect(norm(formatCurrency(1234.5))).toBe("1 234,50 €")
    expect(formatPercent(12, 100)).toBe("12 %")
    expect(formatRate(12.345)).toBe("12,35 %")
    expect(monthName(1)).toBe("Janvier")
    expect(frequencyLabel("monthly")).toBe("Mensuelle")
    expect(dateLocale().code).toBe("fr")
  })

  it("passe aux formats anglais quand la langue change, et la retient", async () => {
    await setLanguage("en")
    expect(appLocale()).toBe("en-GB")
    expect(formatCurrency(1234.5)).toBe("€1,234.50")
    expect(formatPercent(12, 100)).toBe("12%")
    expect(formatRate(12.345)).toBe("12.35%")
    expect(percentSuffix(true)).toBe("%")
    expect(monthName(1)).toBe("January")
    expect(frequencyLabel("monthly")).toBe("Monthly")
    expect(frequencyLabel("inconnue")).toBe("inconnue")
    expect(dateLocale().code).toBe("en-GB")
    expect(safeStorage.getItem("language")).toBe("en")
    expect(document.documentElement.lang).toBe("en")
  })

  it("passe aux formats espagnols (virgule décimale, point des milliers, euro après)", async () => {
    await setLanguage("es")
    expect(appLocale()).toBe("es-ES")
    expect(norm(formatCurrency(1234.5))).toBe("1234,50 €")
    expect(norm(formatCurrency(12345.5))).toBe("12.345,50 €")
    expect(norm(formatRate(12.345))).toBe("12,35 %")
    expect(percentSuffix(true)).toBe("\u00a0%")
    expect(monthName(1)).toBe("Enero")
    expect(frequencyLabel("monthly")).toBe("Mensual")
    expect(dateLocale().code).toBe("es")
    expect(document.documentElement.lang).toBe("es")
  })

  it("garde une clé manquante en français plutôt que d'afficher la clé", async () => {
    await i18n.changeLanguage("en")
    expect(i18n.t("nav:items.dashboard")).toBe("Dashboard")
    expect(i18n.t("urgentActions", { ns: "nav", count: 1 })).toBe("1 urgent action")
    expect(i18n.t("urgentActions", { ns: "nav", count: 3 })).toBe("3 urgent actions")
  })

  it("lit le code de langue sans la région et retombe sur le français pour une langue inconnue", async () => {
    await i18n.changeLanguage("en-US")
    expect(appLocale()).toBe("en-GB")
    await i18n.changeLanguage("de")
    expect(appLocale()).toBe("fr-FR")
    expect(percentSuffix(true)).toBe("\u00a0%")
    expect(percentSuffix()).toBe(" %")
  })
})
