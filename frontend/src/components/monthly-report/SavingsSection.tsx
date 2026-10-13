import { Card, CardContent } from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import type { MonthlyReportData } from "./types"

function Figure({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: string }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`amount-blur text-xl font-black ${tone ?? "text-slate-900"}`}>{value}</div>
      {hint && <div className="amount-blur text-[11px] text-slate-400">{hint}</div>}
    </div>
  )
}

export function SavingsSection({ data }: { data: MonthlyReportData }) {
  const flow = data.money_flow
  const hasExceptional = data.exceptional_expenses > 0
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-black text-slate-900">Mis de côté</h2>
      <Card>
        <CardContent className="grid grid-cols-2 gap-x-6 gap-y-5 p-5 sm:grid-cols-4">
          {flow && <Figure label="Épargne" value={formatCurrency(flow.savings.amount)} />}
          {flow && <Figure label="Investi" value={formatCurrency(flow.investments.amount)} />}
          <Figure
            label="Taux d'épargne"
            value={`${data.savings_rate.toFixed(1)} %`}
            hint={hasExceptional ? `${data.savings_rate_excl_exceptional.toFixed(1)} % hors exceptionnel` : undefined}
          />
          <Figure
            label="Variation du patrimoine"
            value={`${data.net_worth_change >= 0 ? "+" : "−"}${formatCurrency(Math.abs(data.net_worth_change))}`}
            tone={data.net_worth_change >= 0 ? "text-emerald-600" : "text-rose-600"}
          />
        </CardContent>
      </Card>
    </section>
  )
}
