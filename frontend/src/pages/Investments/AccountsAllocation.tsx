import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { formatAmountWithShare, formatCurrency, formatRate } from "@/lib/utils"
import { COLORS } from "./types"
import type { InvestmentsCtx } from "./useInvestments"

/** Section 1 : répartition par comptes. */
export function AccountsAllocation({ ctx }: { ctx: InvestmentsCtx }) {
  const { allocation, chartData, handleAccountClick } = ctx
  return (
    <>
      {/* Section 1: Répartition par comptes */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Répartition par compte</h2>
          <p className="text-sm text-muted-foreground">Vos investissements séparés par enveloppe.</p>
        </div>
        <Card className="shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="flex flex-col items-start justify-between gap-2 border-b bg-slate-50/50 pb-4 sm:flex-row sm:items-center">
            <CardTitle className="text-base font-bold">Détails de l'allocation</CardTitle>
            <span className="text-sm font-semibold text-slate-500 bg-slate-100/80 px-3 py-1 rounded-lg">
              Total : <span className="amount-blur text-slate-900 font-bold">{formatCurrency(allocation?.total_current_value || 0)}</span>
            </span>
          </CardHeader>
          <CardContent className="p-4 md:p-6">
            <div className="grid grid-cols-1 items-center gap-6 md:gap-8 lg:grid-cols-12">
              {/* Donut Chart */}
              <div className="min-w-0 lg:col-span-5 h-[240px] md:h-[300px] flex items-center justify-center relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                    <Pie
                      data={chartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={75}
                      outerRadius={105}
                      paddingAngle={3}
                      dataKey="value"
                      nameKey="name"
                      onClick={(data) => handleAccountClick(data.id)}
                      className="cursor-pointer outline-none"
                    >
                      {chartData.map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value: number, name: string) => [formatAmountWithShare(value, chartData.reduce((s: number, i: any) => s + (i.value || 0), 0)), name]}
                      contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* Center Text (Total) */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total</span>
                  <span className="text-lg font-bold text-slate-800 amount-blur">
                    {formatCurrency(allocation?.total_current_value || 0)}
                  </span>
                  <span className="text-[11px] text-muted-foreground font-medium">
                    {allocation?.items?.length || 0} {allocation?.items?.length > 1 ? "comptes" : "compte"}
                  </span>
                </div>
              </div>

              {/* Détails de l'allocation */}
              <div className="min-w-0 lg:col-span-7 space-y-2.5 md:max-h-[300px] md:overflow-y-auto md:pr-2 scrollbar-thin scrollbar-thumb-slate-200">
                {allocation?.items?.map((item: any, i: number) => (
                  <div 
                    key={i} 
                    className="flex min-h-11 flex-col gap-1 cursor-pointer hover:bg-slate-50/80 p-3 md:p-2.5 rounded-xl border border-slate-100 hover:border-slate-200 transition-all group"
                    onClick={() => handleAccountClick(item.account_id)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2.5">
                        <div 
                          className="h-3 w-3 rounded-full shrink-0" 
                          style={{ backgroundColor: COLORS[i % COLORS.length] }} 
                        />
                        <span className="font-semibold text-sm truncate min-w-0 text-slate-800 group-hover:text-slate-900 transition-colors">
                          {item.account_name} 
                          {item.currency && item.currency !== "EUR" && (
                            <span className="text-xs text-muted-foreground ml-1.5 font-normal">({item.currency})</span>
                          )}
                        </span>
                      </div>
                      <span className="font-bold text-sm text-slate-700 shrink-0 tabular-nums">{formatRate(item.percentage || 0, 1)}</span>
                    </div>
                    <div className="flex flex-wrap justify-between gap-x-2 text-xs text-muted-foreground pl-5.5">
                      <span className="amount-blur font-medium whitespace-nowrap">{formatCurrency(item.current_value)}</span>
                      {item.gain_eur == null ? (
                        <span className="font-medium whitespace-nowrap text-amber-600" title="Aucune valorisation postérieure aux derniers flux de la période">
                          Valeur à actualiser
                        </span>
                      ) : (
                        <span className={`amount-blur font-medium whitespace-nowrap ${item.gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                          {item.gain_eur >= 0 ? "+" : ""}{formatCurrency(item.gain_eur)}
                          {item.performance_pct != null && ` (${formatRate(item.performance_pct, 2, true)})`}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
