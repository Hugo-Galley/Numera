import { ArrowRight, Zap } from "lucide-react"
import { cn, formatCurrency } from "@/lib/utils"
import type { OmniboxCtx } from "./useOmnibox"

/** Résultats : saisie rapide et actions. */
export function QuickActionResults({ ctx }: { ctx: OmniboxCtx }) {
  const { activeIndex, filteredAccounts, filteredActions, filteredNavigation, handleSelect, mainAccount, quickResults, setActiveIndex } = ctx
  return (
    <>
      {quickResults.length > 0 && (
        <div className="mb-4">
          <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
            Saisie rapide
          </h3>
          {quickResults.map((entry) => {
            const resultIdx = filteredNavigation.length + filteredAccounts.length
            const isActive = activeIndex === resultIdx
            const isIncome = entry.entryType === "Entree"
            return (
              <button
                key="quick-entry"
                id={`result-${resultIdx}`}
                onClick={() => handleSelect(entry)}
                onMouseEnter={() => setActiveIndex(resultIdx)}
                className={cn(
                  "group w-full flex min-h-12 items-center justify-between gap-2 px-3 py-2 rounded-xl transition-colors text-left outline-none",
                  isActive ? "bg-slate-100" : "hover:bg-slate-50"
                )}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className={cn(
                    "h-8 w-8 shrink-0 rounded-lg flex items-center justify-center transition-colors",
                    isIncome ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"
                  )}>
                    <Zap className="h-4 w-4" />
                  </div>
                  <div className="flex min-w-0 flex-col">
                    <span className="truncate font-medium text-slate-900">
                      {isIncome ? "Ajouter un revenu" : "Ajouter une dépense"} de {formatCurrency(entry.amount)}
                      {entry.merchant && <> · {entry.merchant}</>}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {mainAccount ? `Sur ${mainAccount.name}, à vérifier avant d'enregistrer` : "Aucun compte courant actif"}
                    </span>
                  </div>
                </div>
                <ArrowRight className={cn("h-4 w-4 text-slate-300 transition-all", isActive ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2")} />
              </button>
            )
          })}
        </div>
      )}

      {filteredActions.length > 0 && (
        <div className="mb-4">
          <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
            Actions
          </h3>
          {filteredActions.map((action, idx) => {
            const resultIdx = filteredNavigation.length + filteredAccounts.length + quickResults.length + idx
            const isActive = activeIndex === resultIdx
            return (
              <button
                key={action.id}
                id={`result-${resultIdx}`}
                onClick={() => handleSelect(action)}
                onMouseEnter={() => setActiveIndex(resultIdx)}
                className={cn(
                  "group w-full flex min-h-12 items-center justify-between gap-2 px-3 py-2 rounded-xl transition-colors text-left outline-none",
                  isActive ? "bg-slate-100" : "hover:bg-slate-50"
                )}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className={cn(
                    "h-8 w-8 shrink-0 rounded-lg flex items-center justify-center transition-colors",
                    isActive ? "bg-white text-slate-900 shadow-sm" : "bg-slate-100 text-slate-600"
                  )}>
                    <action.icon className="h-4 w-4" />
                  </div>
                  <div className="flex min-w-0 flex-col">
                    <span className="truncate font-medium text-slate-900">{action.name}</span>
                    {action.hint && <span className="text-[10px] text-slate-400">{action.hint}</span>}
                  </div>
                </div>
                <ArrowRight className={cn("h-4 w-4 text-slate-300 transition-all", isActive ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2")} />
              </button>
            )
          })}
        </div>
      )}
    </>
  )
}
