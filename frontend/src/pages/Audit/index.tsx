import { AlertTriangle, ArrowRight, ArrowRightLeft, CheckCircle2, Database, LayoutList, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { TransferReview } from "@/components/audit/TransferReview"
import { MerchantCreatorModal, RuleCreatorModal } from "./CreatorModals"
import { useAudit } from "./useAudit"
import { ActionDetail } from "./ActionDetail"
import { ActionList } from "./ActionList"

export default function ActionCenter() {
  const ctx = useAudit()
  const { activeAction, activeActionId, categories, data, error, loadActions, loading, navigate, normMerchant, ruleMerchant, setNormMerchant, setRuleMerchant, view } = ctx

  if (view === "virements") {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" onClick={() => navigate("/audit")} className="-ml-2 h-10 px-2 text-slate-500 md:h-8">
          <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
          Retour au centre d'actions
        </Button>
        <div>
          <div className="mb-1 flex items-center gap-2">
            <ArrowRightLeft className="h-5 w-5 text-slate-700" />
            <h1 className="text-xl font-semibold text-slate-900">Virements internes</h1>
          </div>
          <p className="text-sm text-slate-500">
            Rapproche les mouvements entre tes comptes pour qu'ils ne comptent ni en revenus ni en dépenses.
          </p>
        </div>
        <TransferReview />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-slate-500">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span className="text-sm font-medium">Analyse des actions...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md border border-rose-200 bg-white p-6">
        <div className="mb-2 flex items-center gap-2 text-rose-600">
          <AlertTriangle className="h-5 w-5" />
          <h2 className="text-sm font-semibold">Centre d'actions indisponible</h2>
        </div>
        <p className="mb-4 text-sm text-slate-600">{error}</p>
        <Button onClick={loadActions} variant="outline" size="sm">Relancer l'analyse</Button>
      </div>
    )
  }

  if (!data) return null

  if (activeActionId && activeAction) {
    return (
      <ActionDetail ctx={ctx} />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <LayoutList className="h-5 w-5 text-slate-700" />
            <h1 className="text-xl font-semibold text-slate-900">Centre d'actions</h1>
          </div>
          <p className="text-sm text-slate-500">
            Une liste centralisée des tâches pour maintenir vos finances propres et sous contrôle.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 md:flex">
          <Button onClick={() => navigate("/audit?vue=virements")} variant="outline" className="h-11 gap-2 md:h-10">
            <ArrowRightLeft className="h-4 w-4" />
            Virements internes
          </Button>
          <Button onClick={loadActions} variant="outline" className="h-11 gap-2 md:h-10">
            <RefreshCw className="h-4 w-4" />
            Actualiser
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 sm:flex sm:flex-wrap sm:gap-4">
        <div className="flex min-w-0 flex-col gap-1 rounded-md border border-slate-200 bg-white p-3 sm:min-w-[140px]">
          <p className="text-xs font-medium text-slate-500">Priorité haute</p>
          <p className="text-xl font-semibold text-rose-600">{data.summary.high_priority}</p>
        </div>
        <div className="flex min-w-0 flex-col gap-1 rounded-md border border-slate-200 bg-white p-3 sm:min-w-[140px]">
          <p className="text-xs font-medium text-slate-500">Priorité moyenne</p>
          <p className="text-xl font-semibold text-amber-600">{data.summary.medium_priority}</p>
        </div>
        <div className="flex min-w-0 flex-col gap-1 rounded-md border border-slate-200 bg-white p-3 sm:min-w-[140px]">
          <p className="text-xs font-medium text-slate-500">Suggestions</p>
          <p className="text-xl font-semibold text-slate-700">{data.summary.low_priority}</p>
        </div>
      </div>

      {data.actions.length === 0 ? (
        <div className="rounded-md border border-slate-200 bg-white p-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50">
            <CheckCircle2 className="h-6 w-6 text-emerald-500" />
          </div>
          <h2 className="text-sm font-semibold text-slate-900">Tout est à jour</h2>
          <p className="mt-1 text-sm text-slate-500">
            Félicitations ! Aucune action requise pour le moment. Votre comptabilité est impeccable.
          </p>
        </div>
      ) : (
        <ActionList ctx={ctx} />
      )}

      {ruleMerchant && (
        <RuleCreatorModal 
          merchant={ruleMerchant.merchant}
          suggestedCategoryId={ruleMerchant.catId}
          categories={categories}
          onCreated={loadActions}
          onClose={() => setRuleMerchant(null)}
        />
      )}

      {normMerchant && (
        <MerchantCreatorModal 
          merchant={normMerchant.merchant}
          variants={normMerchant.variants}
          categories={categories}
          onCreated={loadActions}
          onClose={() => setNormMerchant(null)}
        />
      )}

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Database className="h-3.5 w-3.5" />
        Dernière analyse : {new Date(data.summary.checked_at).toLocaleString("fr-FR")}
      </div>
    </div>
  )
}
