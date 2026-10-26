import { useCallback } from "react"
import { useSearchParams } from "react-router-dom"

/**
 * Filtres d'une vue « transactions derrière ce chiffre », portés par l'URL (`?dd_*`) :
 * le retour arrière ferme le panneau et un lien partagé le rouvre. Le panneau
 * (`components/transactions/DrilldownSheet`) est monté une fois dans `AppLayout`.
 */
export interface DrilldownFilters {
  label: string
  month: number
  year: number
  categoryId?: number | null  // null = « Sans catégorie »
  merchantName?: string
  accountId?: number | null
}

/** Période et compte affichés par la page appelante, passés aux composants cliquables. */
export interface DrilldownScope {
  month: number
  year: number
  accountId: number | null
}

const KEYS = ["dd_label", "dd_m", "dd_y", "dd_cat", "dd_merchant", "dd_acc"] as const

export function readDrilldown(params: URLSearchParams): DrilldownFilters | null {
  const label = params.get("dd_label")
  const month = Number(params.get("dd_m"))
  const year = Number(params.get("dd_y"))
  if (!label || !month || !year) return null
  const cat = params.get("dd_cat")
  const acc = params.get("dd_acc")
  return {
    label,
    month,
    year,
    categoryId: cat === null ? undefined : cat === "none" ? null : Number(cat),
    merchantName: params.get("dd_merchant") ?? undefined,
    accountId: acc ? Number(acc) : null,
  }
}

export function useDrilldown() {
  const [, setSearchParams] = useSearchParams()

  const openDrilldown = useCallback(
    (filters: DrilldownFilters) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        KEYS.forEach((k) => next.delete(k))
        next.set("dd_label", filters.label)
        next.set("dd_m", String(filters.month))
        next.set("dd_y", String(filters.year))
        if (filters.categoryId !== undefined) next.set("dd_cat", filters.categoryId === null ? "none" : String(filters.categoryId))
        if (filters.merchantName) next.set("dd_merchant", filters.merchantName)
        if (filters.accountId) next.set("dd_acc", String(filters.accountId))
        return next
      })
    },
    [setSearchParams],
  )

  const closeDrilldown = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      KEYS.forEach((k) => next.delete(k))
      return next
    })
  }, [setSearchParams])

  return { openDrilldown, closeDrilldown }
}
