import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { IconComponent } from "@/components/dashboard/IconComponent"
import { formatCurrency, formatRate } from "@/lib/utils"
import { Delta } from "./Delta"
import type { MonthlyReportData } from "./types"

const PARTS = [
  { key: "fixed_charges", label: "Charges fixes", bar: "bg-slate-700" },
  { key: "variable_expenses", label: "Dépenses variables", bar: "bg-rose-400" },
  { key: "savings", label: "Épargne", bar: "bg-emerald-500" },
  { key: "investments", label: "Investi", bar: "bg-sky-500" },
  { key: "remainder", label: "Reste", bar: "bg-slate-200" },
] as const

export function SpendingSection({ data }: { data: MonthlyReportData }) {
  const flow = data.money_flow
  const parts = flow
    ? PARTS.map((p) => ({ ...p, block: flow[p.key] })).filter((p) => p.block.amount > 0)
    : []
  const total = parts.reduce((sum, p) => sum + p.block.amount, 0)
  const maxCat = Math.max(...data.top_categories.map((c) => c.total), 1)

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-black text-slate-900">Où est passé l'argent ?</h2>
      <Card>
        <CardContent className="space-y-6 p-4 md:p-5">
          {flow && total > 0 && (
            <div className="space-y-3">
              <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100">
                {parts.map((p) => (
                  <div
                    key={p.key}
                    className={p.bar}
                    style={{ width: `${(p.block.amount / total) * 100}%` }}
                    title={`${p.label} : ${formatCurrency(p.block.amount)}`}
                  />
                ))}
              </div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-5">
                {parts.map((p) => (
                  <div key={p.key}>
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <span className={`h-2 w-2 rounded-full ${p.bar}`} />
                      {p.label}
                    </div>
                    <div className="amount-blur text-sm font-bold">{formatCurrency(p.block.amount)}</div>
                    {flow.remainder.amount >= 0 && (
                      <div className="text-[11px] text-slate-400">{formatRate(p.block.percentage, 1)} des revenus</div>
                    )}
                  </div>
                ))}
              </div>
              {flow.remainder.amount < 0 && (
                <p className="text-xs font-medium text-rose-600">
                  Dépenses supérieures aux revenus de{" "}
                  <span className="amount-blur">{formatCurrency(Math.abs(flow.remainder.amount))}</span>.
                </p>
              )}
            </div>
          )}

          <div>
            <CardHeader className="p-0 pb-2">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Principales catégories
              </CardTitle>
            </CardHeader>
            {data.top_categories.length === 0 ? (
              <p className="py-4 text-sm italic text-slate-400">Aucune dépense catégorisée ce mois-ci.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.top_categories.map((c) => (
                  <li key={c.name} className="flex min-h-12 items-center gap-3 py-2.5">
                    <span
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
                      style={{ backgroundColor: `${c.color}1f`, color: c.color }}
                    >
                      <IconComponent name={c.icon} className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="truncate text-sm font-semibold text-slate-800">{c.name}</span>
                        <span className="amount-blur whitespace-nowrap text-sm font-black tabular-nums">
                          {formatCurrency(c.total)}
                        </span>
                      </div>
                      <div className="mt-1.5 flex items-center gap-3">
                        <div className="h-1 flex-1 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${(c.total / maxCat) * 100}%`, backgroundColor: c.color }}
                          />
                        </div>
                        <span className="shrink-0 whitespace-nowrap text-right md:w-28">
                          <Delta diff={c.total - c.prev_total} />
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
