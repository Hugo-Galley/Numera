import { appLocale } from "@/i18n/locale"

/** Montant compact pour une graduation d'axe : « 14 k€ », « 10,5 k€ », « 750 € » (ne déborde jamais de l'axe). */
export function formatCompactCurrency(value: number, currency = "EUR") {
  return new Intl.NumberFormat(appLocale(), {
    style: "currency",
    currency,
    notation: "compact",
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(value)
}
