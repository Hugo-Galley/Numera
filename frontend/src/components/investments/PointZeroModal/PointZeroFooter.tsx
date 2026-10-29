import { Button } from "@/components/ui/button"
import { CheckCircle2 } from "lucide-react"
import type { PointZeroModalCtx } from "./usePointZeroModal"

/** Total calculé et boutons d'enregistrement. */
export function PointZeroFooter({ ctx }: { ctx: PointZeroModalCtx }) {
  const { handleSave, onOpenChange, saving, totalCalculatedEur } = ctx
  return (
    <>
      {/* Footer summary */}
      <div className="flex flex-col gap-3 pt-3 border-t mt-3 sm:pt-4 sm:mt-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col">
          <span className="text-xs text-slate-500">Valeur totale estimée :</span>
          <span className="text-base font-bold font-mono text-slate-900">
            {new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(totalCalculatedEur)}
          </span>
        </div>

        <div className="flex flex-row-reverse gap-2 sm:items-center">
          <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={saving} className="h-11 border-slate-200 text-slate-700 sm:h-8">
            Annuler
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={handleSave}
            disabled={saving}
            className="h-11 flex-1 gap-2 bg-slate-900 text-white shadow-sm hover:bg-slate-800 sm:h-8 sm:flex-none"
          >
            <CheckCircle2 className="h-4 w-4" />
            {saving ? "Enregistrement..." : "Enregistrer l'état des lieux"}
          </Button>
        </div>
      </div>
    </>
  )
}
