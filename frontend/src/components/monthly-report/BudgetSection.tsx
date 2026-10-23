import { Card, CardContent } from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import type { BudgetLine } from "./types"

export function BudgetSection({ lines }: { lines: BudgetLine[] }) {
  const budgeted = lines
    .filter((l) => l.monthly_limit !== null && l.monthly_limit > 0)
    .sort((a, b) => (b.monthly_ratio ?? 0) - (a.monthly_ratio ?? 0))
  if (budgeted.length === 0) return null
  const over = budgeted.filter((l) => (l.monthly_ratio ?? 0) >= 1).length

  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-black text-slate-900">Budget tenu ?</h2>
        <span className={`text-xs font-semibold ${over ? "text-rose-600" : "text-emerald-600"}`}>
          {over ? `${over} dépassement${over > 1 ? "s" : ""}` : "Tous les budgets respectés"}
        </span>
      </div>
      <Card>
        <CardContent className="divide-y divide-slate-100 p-0">
          {budgeted.map((l) => {
            const limit = l.monthly_limit as number
            const ratio = l.monthly_spent / limit
            const left = limit - l.monthly_spent
            const tone = ratio >= 1 ? "bg-rose-500" : ratio >= 0.8 ? "bg-amber-500" : "bg-emerald-500"
            return (
              <div key={l.category_id} className="space-y-1.5 px-4 py-3 md:px-5">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="min-w-0 truncate text-sm font-semibold text-slate-800">{l.category_name}</span>
                  <span className="amount-blur shrink-0 whitespace-nowrap text-sm tabular-nums">
                    <span className="font-black">{formatCurrency(l.monthly_spent)}</span>
                    <span className="text-slate-400"> / {formatCurrency(limit)}</span>
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100 md:h-1.5">
                  <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.min(100, ratio * 100)}%` }} />
                </div>
                <div className={`amount-blur text-xs ${left < 0 ? "font-semibold text-rose-600" : "text-slate-500"}`}>
                  {left < 0 ? `Dépassé de ${formatCurrency(-left)}` : `Reste ${formatCurrency(left)}`}
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>
    </section>
  )
}
