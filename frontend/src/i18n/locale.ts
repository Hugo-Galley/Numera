/**
 * Formats d'affichage liés à la langue de l'interface : nombres, devises, dates.
 * Lit l'instance i18next globale (sans hook), donc utilisable dans les fonctions de `lib/`.
 * Avant l'initialisation de i18n (ou sans langue), le français reste le repli.
 */
import i18n from "i18next"
import { enGB, fr } from "date-fns/locale"

const isEnglish = () => (i18n.language ?? "").startsWith("en")

/** Locale BCP 47 pour `Intl` et `toLocale*String` : `fr-FR` ou `en-GB` (euro d'abord, jour avant mois). */
export const appLocale = () => (isEnglish() ? "en-GB" : "fr-FR")

/** Locale date-fns correspondante. */
export const dateLocale = () => (isEnglish() ? enGB : fr)

/** Pourcentage : « 12 % » en français (espace), « 12% » en anglais. */
export const percentSuffix = (nonBreaking = false) => (isEnglish() ? "%" : nonBreaking ? " %" : " %")

/** Nom du mois (1 à 12) dans la langue de l'interface, première lettre en majuscule : « Janvier », « January ». */
export function monthName(month: number): string {
  const name = new Date(2000, month - 1, 1).toLocaleDateString(appLocale(), { month: "long" })
  return name.charAt(0).toLocaleUpperCase(appLocale()) + name.slice(1)
}
