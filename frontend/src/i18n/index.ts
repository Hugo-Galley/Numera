import i18n from "i18next"
import { initReactI18next } from "react-i18next"
import { safeStorage } from "@/lib/storage"
import frAccounts from "./locales/fr/accounts.json"
import frAuth from "./locales/fr/auth.json"
import frImport from "./locales/fr/import.json"
import frLoans from "./locales/fr/loans.json"
import frCommon from "./locales/fr/common.json"
import frDashboard from "./locales/fr/dashboard.json"
import frNav from "./locales/fr/nav.json"
import frSettings from "./locales/fr/settings.json"
import enAccounts from "./locales/en/accounts.json"
import enAuth from "./locales/en/auth.json"
import enImport from "./locales/en/import.json"
import enLoans from "./locales/en/loans.json"
import enCommon from "./locales/en/common.json"
import enDashboard from "./locales/en/dashboard.json"
import enNav from "./locales/en/nav.json"
import enSettings from "./locales/en/settings.json"

export const LANGUAGES = ["fr", "en"] as const
export type Language = (typeof LANGUAGES)[number]

const STORAGE_KEY = "language"

/** Un catalogue (JSON) par domaine ; le français est la référence, l'anglais doit avoir les mêmes clés. */
export const resources = {
  fr: { common: frCommon, accounts: frAccounts, import: frImport, loans: frLoans, nav: frNav, auth: frAuth, settings: frSettings, dashboard: frDashboard },
  en: { common: enCommon, accounts: enAccounts, import: enImport, loans: enLoans, nav: enNav, auth: enAuth, settings: enSettings, dashboard: enDashboard },
} as const

const isLanguage = (value: unknown): value is Language => LANGUAGES.includes(value as Language)

/** Langue enregistrée sur cet appareil, sinon celle du navigateur (français ou, par défaut, anglais). */
export function detectLanguage(): Language {
  const saved = safeStorage.getItem(STORAGE_KEY)
  if (isLanguage(saved)) return saved
  const browser = typeof navigator === "undefined" ? "" : navigator.language
  return browser.toLowerCase().startsWith("fr") ? "fr" : "en"
}

void i18n.use(initReactI18next).init({
  resources,
  lng: detectLanguage(),
  fallbackLng: "fr",
  defaultNS: "common",
  ns: Object.keys(resources.fr),
  interpolation: { escapeValue: false }, // React échappe déjà
  initAsync: false, // catalogues embarqués : disponibles dès le premier rendu
})

i18n.on("languageChanged", (language) => {
  document.documentElement.lang = language
})
document.documentElement.lang = i18n.language

/** Change la langue de l'interface et la retient pour cet appareil. */
export function setLanguage(language: Language) {
  safeStorage.setItem(STORAGE_KEY, language)
  return i18n.changeLanguage(language)
}

export { i18n }
