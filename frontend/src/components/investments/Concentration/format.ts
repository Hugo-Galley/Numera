import { appLocale } from "@/i18n/locale"

/** Corrélation affichée à deux décimales (« 0,86 »). */
export const formatRho = (rho: number) =>
  new Intl.NumberFormat(appLocale(), { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(rho)

/** Écart en points, signé, au dixième au plus (« +13 », « -4,5 »). */
export const formatPoints = (value: number) =>
  `${value > 0 ? "+" : ""}${new Intl.NumberFormat(appLocale(), { maximumFractionDigits: 1 }).format(value)}`

/** Nombre décimal court (« 3,2 »). */
export const formatDecimal = (value: number) => new Intl.NumberFormat(appLocale(), { maximumFractionDigits: 1 }).format(value)
