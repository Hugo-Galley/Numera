/**
 * Formats d'affichage liés à la langue de l'interface : nombres, devises, dates.
 * Lit l'instance i18next globale (sans hook), donc utilisable dans les fonctions de `lib/`.
 * Avant l'initialisation de i18n (ou sans langue), le français reste le repli.
 */
import i18n from "i18next"
import { enGB, fr } from "date-fns/locale"
import type { Locale } from "date-fns"

interface LocaleConfig {
  /** Locale BCP 47 pour `Intl` et `toLocale*String`. */
  intl: string
  /** Locale date-fns. */
  date: Locale
  /** Suffixe de pourcentage, avec espace ordinaire ou insécable selon le contexte. */
  percent: { regular: string; nonBreaking: string }
}

/**
 * Conventions d'affichage de chaque langue. Ajouter une langue : une entrée ici (clé = code de `LANGUAGES`),
 * son dossier `locales/<code>/` et son code dans `i18n/index.ts`.
 */
const LOCALES = {
  fr: { intl: "fr-FR", date: fr, percent: { regular: " %", nonBreaking: "\u00a0%" } }, // euro d'abord, jour avant mois
  en: { intl: "en-GB", date: enGB, percent: { regular: "%", nonBreaking: "%" } },
} satisfies Record<string, LocaleConfig>

type LocaleCode = keyof typeof LOCALES

const isLocaleCode = (code: string): code is LocaleCode => code in LOCALES

/** Configuration de la langue courante (`fr-CA` → `fr`) ; le français reste le repli. */
function current(): LocaleConfig {
  const code = (i18n.language ?? "").slice(0, 2)
  return isLocaleCode(code) ? LOCALES[code] : LOCALES.fr
}

/** Locale BCP 47 pour `Intl` et `toLocale*String` : `fr-FR` ou `en-GB`. */
export const appLocale = () => current().intl

/** Locale date-fns correspondante. */
export const dateLocale = () => current().date

/** Pourcentage : « 12 % » en français (espace), « 12% » en anglais. */
export const percentSuffix = (nonBreaking = false) => (nonBreaking ? current().percent.nonBreaking : current().percent.regular)

/** Nom du mois (1 à 12) dans la langue de l'interface, première lettre en majuscule : « Janvier », « January ». */
export function monthName(month: number): string {
  const name = new Date(2000, month - 1, 1).toLocaleDateString(appLocale(), { month: "long" })
  return name.charAt(0).toLocaleUpperCase(appLocale()) + name.slice(1)
}

/** Nom court du mois (1 à 12) : « janv. », « juin » en français, « Jan », « Jun » en anglais. */
export function monthShort(month: number): string {
  return new Date(2000, month - 1, 1).toLocaleDateString(appLocale(), { month: "short" })
}
