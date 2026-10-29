import { ArrowRight, CheckCircle2, Link2, RefreshCw, Wrench } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn, formatCurrency } from "@/lib/utils"
import { TransactionEditor } from "./TransactionEditor"
import { actionIconClass, severityClass, severityLabel } from "./types"
import type { AuditCtx } from "./useAudit"

/** Vue détaillée d'une action : transactions, doublons ou virements à traiter. */
export function ActionDetail({ ctx }: { ctx: AuditCtx }) {
  const { accounts, activeActionId, activeIssueId, categories, detail, ignoreDuplicate, ignoreTransfer, linkTransfer, loadingIssueId, removeTransactionFromDetails, setActiveActionId, updateTransactionInDetails } = ctx
  const activeAction = ctx.activeAction!
  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => setActiveActionId(null)} className="-ml-2 h-10 px-2 text-slate-500 md:h-8">
            <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
            Retour au centre d'actions
          </Button>
        </div>

        <div className="flex gap-3">
          <div className={cn("mt-0.5 shrink-0", actionIconClass[activeAction.severity])}>
            <Wrench className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <h1 className="text-lg font-semibold text-slate-900">{activeAction.title}</h1>
              <Badge variant="outline" className={cn("text-[10px] font-medium uppercase tracking-wider", severityClass[activeAction.severity])}>
                {severityLabel[activeAction.severity]}
              </Badge>
            </div>
            <p className="mt-1 max-w-2xl text-sm text-slate-500">{activeAction.description}</p>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-2 sm:p-4 md:p-6">
          {loadingIssueId === activeActionId && (
            <div className="flex h-40 items-center justify-center gap-3 text-slate-500">
              <RefreshCw className="h-5 w-5 animate-spin" />
              <span>Chargement des détails...</span>
            </div>
          )}

          {detail?.transactions && (
            <div className="space-y-3">
              {detail.transactions.map((tx) => (
                <TransactionEditor
                  key={tx.id}
                  tx={tx}
                  categories={categories}
                  accounts={accounts}
                  onSaved={(saved) => activeIssueId && updateTransactionInDetails(activeIssueId, saved)}
                />
              ))}
            </div>
          )}

          {detail?.duplicate_groups && (
            <div className="space-y-6">
              {detail.duplicate_groups.map((group) => (
                <div key={group.key} className="space-y-3">
                  <div className="flex flex-col gap-2 px-1 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
                    <p className="text-sm font-bold text-slate-900">{group.count} transactions identiques détectées</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => ignoreDuplicate(group.transactions)}
                        className="h-10 text-[10px] font-bold uppercase tracking-wider sm:h-7"
                      >
                        Marquer comme OK
                      </Button>
                      <Badge variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100">
                        Action requise
                      </Badge>
                    </div>
                  </div>
                  <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-2 shadow-sm sm:p-3">
                    {group.transactions.map((tx) => (
                      <TransactionEditor
                        key={tx.id}
                        tx={tx}
                        categories={categories}
                        accounts={accounts}
                        onSaved={(saved) => activeIssueId && updateTransactionInDetails(activeIssueId, saved)}
                        onDeleted={(id) => activeIssueId && removeTransactionFromDetails(activeIssueId, id)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {detail?.transfer_pairs && (
            <div className="space-y-6">
              {detail.transfer_pairs.map((pair) => (
                <div key={`${pair.sortie.id}-${pair.entree.id}`} className="space-y-3">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between px-1">
                    <div>
                      <p className="text-sm font-bold text-slate-900">
                        {formatCurrency(pair.sortie.amount, pair.sortie.currency)} entre deux comptes
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-2 md:flex">
                      <Button size="sm" className="h-11 md:h-9" onClick={() => linkTransfer(pair.sortie.id, pair.entree.id)}>
                        <Link2 className="h-4 w-4" />
                        Rapprocher
                      </Button>
                      <Button size="sm" variant="outline" className="h-11 md:h-9" onClick={() => ignoreTransfer(pair.sortie.id)}>
                        Ignorer
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                    <TransactionEditor
                      tx={pair.sortie}
                      categories={categories}
                      accounts={accounts}
                      onSaved={(saved) => activeIssueId && updateTransactionInDetails(activeIssueId, saved)}
                    />
                    <TransactionEditor
                      tx={pair.entree}
                      categories={categories}
                      accounts={accounts}
                      onSaved={(saved) => activeIssueId && updateTransactionInDetails(activeIssueId, saved)}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {detail && !detail.transactions?.length && !detail.duplicate_groups?.length && !detail.transfer_pairs?.length && (
            <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-slate-200 bg-white p-8 text-center">
              <CheckCircle2 className="h-10 w-10 text-emerald-500" />
              <div className="space-y-1">
                <p className="font-bold text-slate-900">Tout est corrigé !</p>
                <p className="text-sm text-slate-500">Il ne reste plus d'éléments à traiter pour cette action.</p>
              </div>
              <Button variant="outline" onClick={() => setActiveActionId(null)} className="mt-2">
                Retourner à la liste
              </Button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
