import { useEffect, useState } from "react"
import { api } from "@/lib/api"

export interface BudgetPeriod {
  year: number
  month: number
  mode: "civil" | "salary"
  start: string
  end: string
  current: { year: number; month: number }
}

const SHORT_DATE: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" }

/** « 25 août → 25 sept. » : fenêtre du mois budgétaire (affichée seulement en mode paie). */
export function formatPeriodRange(period: BudgetPeriod | null): string | null {
  if (!period || period.mode !== "salary") return null
  const fmt = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString("fr-FR", SHORT_DATE)
  return `${fmt(period.start)} → ${fmt(period.end)}`
}

/** Fenêtre du mois budgétaire `year`/`month` ; `null` tant que la réponse n'est pas arrivée. */
export function useBudgetPeriod(year: number, month: number): BudgetPeriod | null {
  const [period, setPeriod] = useState<BudgetPeriod | null>(null)
  useEffect(() => {
    let cancelled = false
    api
      .get<BudgetPeriod>(`/analytics/budget-period?year=${year}&month=${month}`)
      .then(res => {
        if (!cancelled) setPeriod(res)
      })
      .catch(() => {
        if (!cancelled) setPeriod(null)
      })
    return () => {
      cancelled = true
    }
  }, [year, month])
  return period
}

/** Mois budgétaire en cours (celui du dernier salaire reçu) : `null` en cas d'échec, l'appelant garde le mois civil. */
export async function fetchCurrentBudgetMonth(): Promise<{ year: number; month: number } | null> {
  try {
    const res = await api.get<BudgetPeriod>("/analytics/budget-period")
    return res.current
  } catch {
    return null
  }
}
