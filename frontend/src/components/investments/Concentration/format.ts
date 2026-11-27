import { appLocale } from "@/i18n/locale"
import { formatRate } from "@/lib/utils"
import type { MarketDimension } from "@/types/diversity"

/** Corrélation affichée à deux décimales (« 0,86 »). */
export const formatRho = (rho: number) =>
  new Intl.NumberFormat(appLocale(), { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(rho)

/** Écart en points, signé, au dixième au plus (« +13 », « -4,5 »). */
export const formatPoints = (value: number) =>
  `${value > 0 ? "+" : ""}${new Intl.NumberFormat(appLocale(), { maximumFractionDigits: 1 }).format(value)}`

/** Nombre décimal court (« 3,2 »). */
export const formatDecimal = (value: number) => new Intl.NumberFormat(appLocale(), { maximumFractionDigits: 1 }).format(value)

/** Active share d'une dimension ; « — » quand rien n'y est comparable (composition inconnue), jamais un faux 0 %. */
export const activeShare = (dimension: MarketDimension) =>
  dimension.covered_pct > 0 ? formatRate(dimension.active_share_pct, 0) : "—"
