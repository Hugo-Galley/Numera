import { formatCurrency } from "@/lib/utils"
import { IconComponent } from "../IconComponent"

interface BudgetsTabProps {
  budgetAlerts: any[]
}

export function BudgetsTab({ budgetAlerts }: BudgetsTabProps) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-xl font-bold text-slate-900">Suivi des budgets</h2>
        <p className="text-sm text-slate-500">Visualisez votre consommation par rapport aux limites fixées par catégorie.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {budgetAlerts.map((alert) => {
          const monthlyOver = alert.monthly_ratio != null && alert.monthly_ratio >= 1
          const annualOver = alert.annual_ratio != null && alert.annual_ratio >= 1
          const monthlyWarning = alert.monthly_ratio != null && alert.monthly_ratio >= 0.8
          const annualWarning = alert.annual_ratio != null && alert.annual_ratio >= 0.8
          
          const monthlyPct = alert.monthly_ratio != null ? Math.round(alert.monthly_ratio * 100) : null
          const annualPct = alert.annual_ratio != null ? Math.round(alert.annual_ratio * 100) : null
          
          const isOver = monthlyOver || annualOver
          const isWarning = monthlyWarning || annualWarning

          return (
            <div
              key={alert.category_id}
              className={`p-5 rounded-2xl border flex flex-col gap-4 transition-all shadow-sm ${
                isOver 
                  ? "bg-rose-50 border-rose-200" 
                  : isWarning 
                    ? "bg-amber-50 border-amber-200" 
                    : "bg-white border-slate-100 hover:border-slate-200"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl flex items-center justify-center shadow-sm" style={{ backgroundColor: alert.category_color || "#64748b" }}>
                  <IconComponent name={alert.category_icon} className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="font-bold text-slate-900">{alert.category_name}</p>
                  <p className={`text-[10px] font-black uppercase tracking-wider ${
                    isOver ? "text-rose-500" : isWarning ? "text-amber-500" : "text-emerald-500"
                  }`}>
                    {isOver ? "Dépassement" : isWarning ? "Proche de la limite" : "Budget respecté"}
                  </p>
                </div>
              </div>
              {monthlyPct != null && (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-slate-500 font-medium">
                    <span>Mensuel — <span className="amount-blur">{formatCurrency(alert.monthly_spent)}</span> / <span className="amount-blur">{formatCurrency(alert.monthly_limit)}</span></span>
                    <span className={`font-bold amount-blur ${monthlyOver ? "text-rose-600" : monthlyWarning ? "text-amber-600" : "text-slate-600"}`}>{monthlyPct}%</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        monthlyOver ? "bg-rose-500" : monthlyWarning ? "bg-amber-400" : "bg-emerald-400"
                      }`}
                      style={{ width: `${Math.min(monthlyPct, 100)}%` }}
                    />
                  </div>
                </div>
              )}
              {annualPct != null && (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-slate-500 font-medium">
                    <span>Annuel — <span className="amount-blur">{formatCurrency(alert.annual_spent)}</span> / <span className="amount-blur">{formatCurrency(alert.annual_limit)}</span></span>
                    <span className={`font-bold amount-blur ${annualOver ? "text-rose-600" : annualWarning ? "text-amber-600" : "text-slate-600"}`}>{annualPct}%</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        annualOver ? "bg-rose-500" : annualWarning ? "bg-amber-400" : "bg-emerald-400"
                      }`}
                      style={{ width: `${Math.min(annualPct, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )
        })}
        {budgetAlerts.length === 0 && (
          <div className="col-span-full py-20 text-center bg-slate-50 rounded-3xl border border-dashed">
            <p className="text-slate-400">Aucun budget configuré. Ajoutez des limites dans les réglages des catégories.</p>
          </div>
        )}
      </div>
    </div>
  )
}
