import i18n from "i18next"
import { initReactI18next } from "react-i18next"
import { safeStorage } from "@/lib/storage"
import frAccounts from "./locales/fr/accounts.json"
import frAuth from "./locales/fr/auth.json"
import frImport from "./locales/fr/import.json"
import frLoans from "./locales/fr/loans.json"
import frAccountDetail from "./locales/fr/accountDetail.json"
import frTransactions from "./locales/fr/transactions.json"
import frInvestments from "./locales/fr/investments.json"
import frOmnibox from "./locales/fr/omnibox.json"
import frSavings from "./locales/fr/savings.json"
import frRecurring from "./locales/fr/recurring.json"
import frReimbursements from "./locales/fr/reimbursements.json"
import frMonth from "./locales/fr/month.json"
import frClassement from "./locales/fr/classement.json"
import frAudit from "./locales/fr/audit.json"
import frTax from "./locales/fr/tax.json"
import frTools from "./locales/fr/tools.json"
import frWrapped from "./locales/fr/wrapped.json"
import frCommon from "./locales/fr/common.json"
import frDashboard from "./locales/fr/dashboard.json"
import frNav from "./locales/fr/nav.json"
import frSettings from "./locales/fr/settings.json"
import enAccounts from "./locales/en/accounts.json"
import enAuth from "./locales/en/auth.json"
import enImport from "./locales/en/import.json"
import enLoans from "./locales/en/loans.json"
import enAccountDetail from "./locales/en/accountDetail.json"
import enTransactions from "./locales/en/transactions.json"
import enInvestments from "./locales/en/investments.json"
import enOmnibox from "./locales/en/omnibox.json"
import enSavings from "./locales/en/savings.json"
import enRecurring from "./locales/en/recurring.json"
import enReimbursements from "./locales/en/reimbursements.json"
import enMonth from "./locales/en/month.json"
import enClassement from "./locales/en/classement.json"
import enAudit from "./locales/en/audit.json"
import enTax from "./locales/en/tax.json"
import enTools from "./locales/en/tools.json"
import enWrapped from "./locales/en/wrapped.json"
import enCommon from "./locales/en/common.json"
import enDashboard from "./locales/en/dashboard.json"
import enNav from "./locales/en/nav.json"
import enSettings from "./locales/en/settings.json"
import { resetApiCache } from "@/lib/apiCache"

export const LANGUAGES = ["fr", "en"] as const
export type Language = (typeof LANGUAGES)[number]

const STORAGE_KEY = "language"

/** Un catalogue (JSON) par domaine ; le français est la référence, l'anglais doit avoir les mêmes clés. */
export const resources = {
  fr: { common: frCommon, accounts: frAccounts, accountDetail: frAccountDetail, import: frImport, loans: frLoans, transactions: frTransactions, investments: frInvestments, omnibox: frOmnibox, savings: frSavings, recurring: frRecurring, reimbursements: frReimbursements, month: frMonth, classement: frClassement, audit: frAudit, tax: frTax, tools: frTools, wrapped: frWrapped, nav: frNav, auth: frAuth, settings: frSettings, dashboard: frDashboard },
  en: { common: enCommon, accounts: enAccounts, accountDetail: enAccountDetail, import: enImport, loans: enLoans, transactions: enTransactions, investments: enInvestments, omnibox: enOmnibox, savings: enSavings, recurring: enRecurring, reimbursements: enReimbursements, month: enMonth, classement: enClassement, audit: enAudit, tax: enTax, tools: enTools, wrapped: enWrapped, nav: enNav, auth: enAuth, settings: enSettings, dashboard: enDashboard },
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
  // Les réponses mises en cache portent des textes du serveur dans l'ancienne langue
  resetApiCache()
  return i18n.changeLanguage(language)
}

export { i18n }
