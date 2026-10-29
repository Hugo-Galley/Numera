import { ArrowRightLeft, HandCoins, Repeat } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { IconComponent } from "@/components/dashboard/IconComponent"
import { format } from "date-fns"
import type { AccountDetailView } from "./useAccountDetail"

/** Liste des transactions en cartes (mobile). */
export function TransactionsMobileList({ ctx }: { ctx: AccountDetailView }) {
  const { account, filteredTransactions, formatCurrency, formatValue, id, renderTxMenu, selectedIds, setSelectedIds, txLoading } = ctx
  return (
    <>
      <div className={`space-y-2 md:hidden transition-opacity ${txLoading ? "opacity-50" : ""}`}>
        {filteredTransactions.length > 0 && (
          <label className="flex min-h-11 items-center gap-3 px-1 text-sm text-slate-500">
            <Checkbox
              checked={selectedIds.length === filteredTransactions.length && filteredTransactions.length > 0}
              onCheckedChange={(checked) => setSelectedIds(checked ? filteredTransactions.map(t => t.id) : [])}
            />
            Tout sélectionner
          </label>
        )}
        {filteredTransactions.map((tx) => {
          const sign = tx.type === "Sortie" ? "-" : (tx.type === "Entree" || tx.type === "Interets") ? "+" : ""
          const tone = tx.type === "Sortie" ? "text-rose-600" : (tx.type === "Entree" || tx.type === "Interets") ? "text-emerald-600" : "text-slate-900"
          return (
            <div key={tx.id} className={`flex items-start gap-1 rounded-xl border bg-white p-2 shadow-sm ${selectedIds.includes(tx.id) ? "border-indigo-300 bg-indigo-50/40" : "border-slate-100"}`}>
              <label className="flex h-10 w-9 shrink-0 cursor-pointer items-center justify-center">
                <Checkbox
                  checked={selectedIds.includes(tx.id)}
                  onCheckedChange={(checked) => {
                    if (checked) setSelectedIds(prev => [...prev, tx.id])
                    else setSelectedIds(prev => prev.filter(id => id !== tx.id))
                  }}
                />
              </label>
              <div className="min-w-0 flex-1 py-1">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-1.5">
                    {tx.recurring_logo && <CompanyLogo logo={tx.recurring_logo} name={tx.merchant} className="h-6 w-6 shrink-0 rounded-md" />}
                    {tx.merchant_obj && <div className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: tx.merchant_obj.color || "#64748b" }} />}
                    <span className="break-words text-sm font-bold leading-tight text-slate-900">{tx.merchant_obj?.name || tx.merchant}</span>
                    {tx.is_recurring && <Repeat className="h-3 w-3 shrink-0 text-indigo-500" />}
                  </div>
                  <span className={`shrink-0 whitespace-nowrap text-sm font-bold tabular-nums amount-blur ${tone}`}>
                    {sign}{formatCurrency(tx.amount)}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center justify-between gap-x-2 gap-y-0.5 text-xs text-slate-500">
                  <div className="flex min-w-0 flex-wrap items-center gap-x-1.5">
                    <span className="shrink-0">{format(new Date(tx.date), "dd/MM/yy")}</span>
                    <span className="text-slate-300">·</span>
                    {tx.type === "Solde Initial" ? (
                      <span>Solde Initial</span>
                    ) : tx.type === "Interets" ? (
                      <span className="text-amber-700">Intérêts</span>
                    ) : (
                      <>
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded" style={{ backgroundColor: tx.category?.color || "#cbd5e1" }}>
                          <IconComponent name={tx.category?.icon} className="h-2.5 w-2.5 text-white" />
                        </span>
                        <span>{tx.splits?.length ? `Découpée · ${tx.splits.map((p: any) => p.category?.name ?? "?").join(", ")}` : tx.category?.name || "Sans catégorie"}</span>
                      </>
                    )}
                  </div>
                  <span className="shrink-0 whitespace-nowrap tabular-nums text-slate-400 amount-blur">Solde {formatCurrency(tx.running_balance)}</span>
                </div>
                {tx.merchant_obj && tx.merchant_obj.name !== tx.merchant && (
                  <p className="mt-0.5 truncate text-[11px] italic text-slate-400">{tx.merchant}</p>
                )}
                {tx.note && <p className="mt-0.5 break-words text-[11px] text-slate-400">{tx.note}</p>}
                {((tx.reimbursement_offset ?? 0) > 0 || tx.is_transfer || (tx.tags && tx.tags.length > 0) || tx.currency !== account.currency) && (
                  <div className="mt-1.5 flex flex-wrap items-center gap-1">
                    {tx.tags?.map((tag: any) => (
                      <Badge key={tag.id} className="border-none px-1.5 py-0 text-[10px] font-bold text-white" style={{ backgroundColor: tag.color || "#64748b" }}>{tag.name}</Badge>
                    ))}
                    {tx.is_transfer && <Badge variant="outline" className="gap-1 border-none bg-emerald-50 px-1.5 py-0 text-[10px] text-emerald-700"><ArrowRightLeft className="h-3 w-3" />Virement</Badge>}
                    {(tx.reimbursement_offset ?? 0) > 0 && (
                      <Badge variant="outline" className="gap-1 border-none bg-emerald-50 px-1.5 py-0 text-[10px] text-emerald-700 amount-blur">
                        <HandCoins className="h-3 w-3" />net {formatCurrency(tx.amount - (tx.reimbursement_offset ?? 0))}
                      </Badge>
                    )}
                    {tx.currency !== account.currency && (
                      <span className="text-[10px] text-slate-400 amount-blur">({formatValue(tx.original_amount, tx.currency)})</span>
                    )}
                  </div>
                )}
              </div>
              {renderTxMenu(tx)}
            </div>
          )
        })}
      </div>
    </>
  )
}
