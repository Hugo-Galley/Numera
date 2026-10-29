import { Button } from "@/components/ui/button"
import { Play, Plus } from "lucide-react"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** En-tête : titre, choix de la vue et boutons d'action. */
export function RecurringHeader({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { changeRecurringView, handleOpenCreate, handleTrigger, handleTriggerBusy, recurringView } = ctx
  return (
    <>
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Échéances</h1>
          <p className="text-slate-500">Récurrences, abonnements, calendrier des flux et salaire.</p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex">
          <div className="col-span-2 flex items-center gap-1 rounded-xl bg-slate-100 p-1 sm:col-span-1" role="group" aria-label="Vue des récurrences">
            <Button
              variant={recurringView === "analysis" ? "white" : "ghost"}
              size="sm"
              className={`h-9 flex-1 rounded-lg px-3 text-xs font-bold ${recurringView === "analysis" ? "shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
              onClick={() => changeRecurringView("analysis")}
            >
              Analyse
            </Button>
            <Button
              variant={recurringView === "list" ? "white" : "ghost"}
              size="sm"
              className={`h-9 flex-1 rounded-lg px-3 text-xs font-bold ${recurringView === "list" ? "shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
              onClick={() => changeRecurringView("list")}
            >
              Liste
            </Button>
          </div>
          <Button variant="outline" onClick={() => handleTrigger()} disabled={handleTriggerBusy} className="h-11 gap-2 px-3 md:h-9">
            <Play className="h-4 w-4" />
            Lancer la génération
          </Button>
          <Button onClick={handleOpenCreate} className="h-11 gap-2 px-3 md:h-9">
            <Plus className="h-4 w-4" />
            Nouvelle récurrence
          </Button>
        </div>
      </div>
    </>
  )
}
