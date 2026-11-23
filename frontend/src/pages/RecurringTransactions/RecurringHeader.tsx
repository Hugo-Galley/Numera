import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Play, Plus } from "lucide-react"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** En-tête : titre, choix de la vue et boutons d'action. */
export function RecurringHeader({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { t } = useTranslation("recurring")
  const { activeTab, changeRecurringView, handleOpenCreate, handleTrigger, handleTriggerBusy, recurringView } = ctx
  // « Analyse / Liste » et la génération ne concernent que l'onglet Récurrences (rien à faire sur Calendrier ou Salaire)
  const onRecurrences = activeTab === "recurring" || activeTab === "subscriptions"
  return (
    <>
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">{t("recurringHeader.echeances")}</h1>
          <p className="text-slate-500">{t("recurringHeader.recurrencesAbonnementsCalendrierDesFlux")}</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          {onRecurrences && (
            <div className="flex items-center gap-1 rounded-xl bg-slate-100 p-1" role="group" aria-label={t("recurringHeader.vueDesRecurrences")}>
              <Button
                variant={recurringView === "analysis" ? "white" : "ghost"}
                size="sm"
                className={`h-9 flex-1 rounded-lg px-3 text-xs font-bold ${recurringView === "analysis" ? "shadow-xs" : "text-slate-500 hover:text-slate-900"}`}
                onClick={() => changeRecurringView("analysis")}
              >
                {t("recurringHeader.analyse")}
              </Button>
              <Button
                variant={recurringView === "list" ? "white" : "ghost"}
                size="sm"
                className={`h-9 flex-1 rounded-lg px-3 text-xs font-bold ${recurringView === "list" ? "shadow-xs" : "text-slate-500 hover:text-slate-900"}`}
                onClick={() => changeRecurringView("list")}
              >
                {t("recurringHeader.liste")}
              </Button>
            </div>
          )}
          <Button onClick={handleOpenCreate} className="h-11 gap-2 px-3 md:h-9 sm:order-last">
            <Plus className="h-4 w-4" />
            {t("recurringHeader.nouvelleRecurrence")}
          </Button>
          {onRecurrences && (
            // Action d'entretien (la génération tourne seule toutes les heures) : discrète sur mobile
            <Button
              variant="outline"
              onClick={() => handleTrigger()}
              disabled={handleTriggerBusy}
              className="h-10 gap-2 self-center border-transparent px-3 text-slate-600 shadow-none sm:self-auto sm:border-slate-200 sm:shadow-xs md:h-9"
            >
              <Play className="h-4 w-4" />
              {t("recurringHeader.lancerLaGeneration")}
            </Button>
          )}
        </div>
      </div>
    </>
  )
}
