import { Activity, AlertTriangle, ShieldCheck, TrendingUp, Wallet } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { InvestmentsCtx } from "./useInvestments"

/** Indicateurs et alertes de surexposition. */
export function InvestmentsKpis({ ctx }: { ctx: InvestmentsCtx }) {
  const { allocation, diversity } = ctx
  return (
    <>
      {/* KPI Section */}
      <div className={`grid gap-3 grid-cols-2 md:gap-4 ${diversity ? "md:grid-cols-4" : "md:grid-cols-3"}`}>
        <Card className="theme-island col-span-2 bg-slate-900 text-white shadow-md border-slate-800 md:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Valeur Totale</CardTitle>
            <TrendingUp className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tabular-nums">
              <span className="amount-blur">{formatCurrency(allocation?.total_current_value || 0)}</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">Positions × cours (comptes titres) et derniers relevés (assurance-vie)</p>
          </CardContent>
        </Card>

        <Card className="col-span-2 shadow-sm md:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Performance Globale</CardTitle>
            <Activity className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold tabular-nums md:text-3xl ${allocation?.total_gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
              <span className="amount-blur">
                {allocation?.total_gain_eur >= 0 ? "+" : ""}{formatCurrency(allocation?.total_gain_eur || 0)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {formatRate(allocation?.total_performance_pct || 0)} de rendement total
            </p>
          </CardContent>
        </Card>

        <Card className={`shadow-sm ${diversity ? "" : "col-span-2 md:col-span-1"}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Supports</CardTitle>
            <Wallet className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold md:text-3xl">{allocation?.items.length || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Comptes d'investissement</p>
          </CardContent>
        </Card>

        {diversity && (
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Score de Diversité</CardTitle>
              <ShieldCheck className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold md:text-3xl">{Number(diversity.score).toLocaleString("fr-FR", { maximumFractionDigits: 1 })}</span>
                <span className="text-sm text-muted-foreground">/100</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">{diversity.score_label}</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Alertes de surexposition (discret) */}
      {diversity && diversity.alerts.length > 0 && (
        <details className="group text-xs text-muted-foreground">
          <summary className="flex min-h-11 w-fit cursor-pointer select-none items-center gap-1.5 hover:text-foreground md:min-h-0">
            <AlertTriangle className="h-3 w-3" />
            {diversity.alerts.length} alerte{diversity.alerts.length > 1 ? "s" : ""} de surexposition
          </summary>
          <ul className="mt-2 space-y-1 pl-4.5 border-l ml-1.5 pl-3">
            {diversity.alerts.map((alert, idx) => (
              <li key={idx}>
                <span className="font-medium text-foreground/80">{alert.title}</span> · {alert.message}
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  )
}
