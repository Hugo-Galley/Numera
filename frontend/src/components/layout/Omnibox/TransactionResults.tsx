import { Receipt, Search } from "lucide-react"
import { cn, formatCurrency } from "@/lib/utils"
import type { OmniboxCtx } from "./useOmnibox"

/** Résultats : transactions et état vide. */
export function TransactionResults({ ctx }: { ctx: OmniboxCtx }) {
  const { activeIndex, asTransactionResult, filteredAccounts, filteredActions, filteredNavigation, handleSelect, isPrivacyMode, loading, query, quickResults, results, searchFailed, setActiveIndex, transactions } = ctx
  return (
    <>
      {transactions.length > 0 && (
        <div className="mb-2">
          <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
            Transactions récentes
          </h3>
          {transactions.map((tx, idx) => {
            const resultIdx = filteredNavigation.length + filteredAccounts.length + quickResults.length + filteredActions.length + idx
            const isActive = activeIndex === resultIdx
            return (
              <button
                key={tx.id}
                id={`result-${resultIdx}`}
                onClick={() => handleSelect(asTransactionResult(tx))}
                onMouseEnter={() => setActiveIndex(resultIdx)}
                className={cn(
                  "group w-full flex min-h-12 items-center justify-between gap-2 px-3 py-2 rounded-xl transition-colors text-left outline-none",
                  isActive ? "bg-slate-100" : "hover:bg-slate-50"
                )}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className={cn(
                    "h-8 w-8 shrink-0 rounded-lg flex items-center justify-center transition-colors",
                    isActive ? "bg-white text-slate-900 shadow-sm" : "bg-slate-50 text-slate-500"
                  )}>
                    <Receipt className="h-4 w-4" />
                  </div>
                  <div className="flex min-w-0 flex-col">
                    <span className="font-medium text-slate-900 truncate sm:max-w-[300px]">
                      {tx.merchant_obj?.name || tx.merchant}
                    </span>
                    <span className="text-[10px] text-slate-400 flex items-center gap-1.5 truncate">
                      {new Date(tx.date).toLocaleDateString("fr-FR")}
                      {tx.merchant_obj && tx.merchant_obj.name !== tx.merchant && <span className="italic">• {tx.merchant}</span>}
                      {tx.note && <span className="italic">• {tx.note}</span>}
                    </span>
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  {/* Le montant est toujours positif en base : le sens vient du type */}
                  <span className={cn(
                    "whitespace-nowrap text-sm font-bold tabular-nums",
                    tx.type === "Sortie" ? "text-rose-600" : tx.type === "Solde Initial" ? "text-slate-600" : "text-emerald-600"
                  )}>
                    {isPrivacyMode ? "****" : `${tx.type === "Sortie" ? "- " : tx.type === "Solde Initial" ? "" : "+ "}${formatCurrency(tx.amount, tx.currency)}`}
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      )}

      {query && !loading && results.length === 0 && (
        <div className="py-12 text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-slate-50 mb-3 text-slate-300">
             <Search className="h-6 w-6" />
          </div>
          <p className="text-slate-500 font-medium">{searchFailed ? "La recherche est momentanément indisponible." : `Aucun résultat pour "${query}"`}</p>
          <p className="text-xs text-slate-400 mt-1">Essayez un autre mot-clé ou vérifiez l'orthographe.</p>
        </div>
      )}
    </>
  )
}
