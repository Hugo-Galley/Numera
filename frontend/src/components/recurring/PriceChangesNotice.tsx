import { TrendingUp } from "lucide-react"
import { format, parseISO } from "date-fns"

import { cn, formatCurrency } from "@/lib/utils"

export interface SubscriptionPriceChange {
  id: string
  name: string
  currency: string
  frequency: "monthly" | "quarterly" | "yearly"
  old_amount: number
  new_amount: number
  delta_pct: number
  annual_impact: number
  changed_on: string
}

const PERIOD_LABEL: Record<SubscriptionPriceChange["frequency"], string> = { monthly: "mois", quarterly: "trim.", yearly: "an" }

/** Hausses de prix récentes détectées par `/analytics/subscriptions` (`price_changes`). */
export function PriceChangesNotice({ changes, className }: { changes?: SubscriptionPriceChange[]; className?: string }) {
  if (!changes?.length) return null
  return (
    <div className={cn("space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-3", className)}>
      <p className="flex items-center gap-2 text-sm font-semibold text-amber-900">
        <TrendingUp className="h-4 w-4" /> Hausses de prix récentes
      </p>
      {changes.map((c) => (
        <div key={c.id} className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm text-amber-900">
          <span className="min-w-0 truncate font-medium">{c.name}</span>
          <span className="tabular-nums">
            {formatCurrency(c.old_amount, c.currency)} → <strong>{formatCurrency(c.new_amount, c.currency)}</strong>
            <span className="text-amber-700"> / {PERIOD_LABEL[c.frequency]} ({c.delta_pct > 0 ? "+" : ""}{c.delta_pct.toLocaleString("fr-FR")} %)</span>
          </span>
          <span className="w-full text-xs text-amber-700">
            Depuis le {format(parseISO(c.changed_on), "dd/MM/yyyy")} · {formatCurrency(c.annual_impact, c.currency)} de plus par an
          </span>
        </div>
      ))}
    </div>
  )
}
