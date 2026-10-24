import { format } from "date-fns"

/**
 * Les dates de l'API sont des datetimes naïfs affichés tels quels (heure du mur), comme l'import CSV.
 * On ne passe donc jamais par `toISOString()` (UTC) : il décalait la date d'1-2 h à chaque enregistrement
 * et pouvait changer le jour ou le mois (audit F1).
 */

const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/
const HAS_ZONE = /(Z|[+-]\d{2}:?\d{2})$/

/** Valeur initiale d'un `<input type="datetime-local">` : maintenant, en heure locale. */
export const nowLocalInput = () => format(new Date(), "yyyy-MM-dd'T'HH:mm")

/** Valeur initiale d'un `<input type="date">` : aujourd'hui, en heure locale. */
export const todayLocal = () => format(new Date(), "yyyy-MM-dd")

/** Date de l'API → valeur d'un `<input type="datetime-local">` (heure du mur, sans conversion). */
export function toInputValue(value: string | null | undefined): string {
  if (!value) return ""
  if (DATE_ONLY.test(value)) return `${value}T00:00`
  if (HAS_ZONE.test(value)) {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? "" : format(date, "yyyy-MM-dd'T'HH:mm")
  }
  return value.slice(0, 16)
}

/** Valeur d'un champ date / datetime-local → chaîne naïve (sans `Z`) à envoyer à l'API. */
export function toNaiveLocal(value: string): string {
  if (DATE_ONLY.test(value)) return `${value}T00:00:00`
  if (HAS_ZONE.test(value)) return format(new Date(value), "yyyy-MM-dd'T'HH:mm:ss")
  return value.length === 16 ? `${value}:00` : value.slice(0, 19)
}

/** Début de la journée choisie (filtre « du »). */
export const startOfDayParam = (day: string) => `${day.slice(0, 10)}T00:00:00`

/** Fin de la journée choisie (filtre « au ») : sans cela le dernier jour était exclu (audit F2). */
export const endOfDayParam = (day: string) => `${day.slice(0, 10)}T23:59:59`
