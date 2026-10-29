import { ArrowRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { accountTypeLabel } from "@/lib/labels"
import { cn, formatCurrency } from "@/lib/utils"
import type { OmniboxCtx } from "./useOmnibox"

/** Résultats : vues et comptes. */
export function NavAccountResults({ ctx }: { ctx: OmniboxCtx }) {
  const { activeIndex, filteredAccounts, filteredNavigation, handleSelect, isPrivacyMode, setActiveIndex } = ctx
  return (
    <>
      {filteredNavigation.length > 0 && (
        <div className="mb-4">
          <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
            Navigation
          </h3>
          {filteredNavigation.map((item, idx) => {
            const resultIdx = idx
            const isActive = activeIndex === resultIdx
            return (
              <button
                key={item.href}
                id={`result-${resultIdx}`}
                onClick={() => handleSelect(item)}
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
                    <item.icon className="h-4 w-4" />
                  </div>
                  <span className="truncate font-medium text-slate-900">{item.name}</span>
                </div>
                <ArrowRight className={cn(
                  "h-4 w-4 text-slate-300 transition-all",
                  isActive ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2"
                )} />
              </button>
            )
          })}
        </div>
      )}

      {filteredAccounts.length > 0 && (
        <div className="mb-4">
          <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
            Comptes
          </h3>
          {filteredAccounts.map((acc, idx) => {
            const resultIdx = filteredNavigation.length + idx
            const isActive = activeIndex === resultIdx
            return (
              <button
                key={acc.id}
                id={`result-${resultIdx}`}
                onClick={() => handleSelect(acc)}
                onMouseEnter={() => setActiveIndex(resultIdx)}
                className={cn(
                  "group w-full flex min-h-12 items-center justify-between gap-2 px-3 py-2 rounded-xl transition-colors text-left outline-none",
                  isActive ? "bg-slate-100" : "hover:bg-slate-50"
                )}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className={cn(
                    "h-8 w-8 shrink-0 rounded-lg flex items-center justify-center font-bold text-[10px] uppercase transition-colors",
                    isActive ? "bg-white text-blue-600 shadow-sm" : "bg-blue-50 text-blue-600"
                  )}>
                    {acc.type.substring(0, 2)}
                  </div>
                  <div className="flex min-w-0 flex-col">
                    <span className="truncate font-medium text-slate-900">{acc.name}</span>
                    <span className="text-[10px] text-slate-400 uppercase font-bold tracking-tight">{accountTypeLabel(acc.type)}</span>
                  </div>
                </div>
                <Badge variant="outline" className={cn(
                  "shrink-0 whitespace-nowrap text-[10px] border-slate-200 text-slate-500",
                  isActive && "bg-white"
                )}>
                  {isPrivacyMode ? "****" : formatCurrency(acc.balance, acc.currency)}
                </Badge>
              </button>
            )
          })}
        </div>
      )}
    </>
  )
}
