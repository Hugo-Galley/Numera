import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { InvestmentsCtx } from "./useInvestments"

/** Dialogue de détail d'une part du graphique. */
export function DrillDownDialog({ ctx }: { ctx: InvestmentsCtx }) {
  const { drillDown, handleAccountClick, setDrillDown } = ctx
  return (
    <>
      <Dialog open={!!drillDown} onOpenChange={(open) => !open && setDrillDown(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{drillDown?.title}</DialogTitle>
            <DialogDescription>
              Détail des comptes contribuant à cette catégorie.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-2 space-y-2.5 md:mt-4 md:space-y-4">
            {(drillDown?.items || []).map((item: any, i: number) => (
              <div 
                key={i} 
                className="flex min-h-12 items-center justify-between gap-3 p-3 rounded-lg border bg-slate-50/50 cursor-pointer hover:bg-slate-50 transition-colors group"
                onClick={() => {
                  setDrillDown(null)
                  handleAccountClick(item.account_id)
                }}
              >
                <div className="flex min-w-0 flex-col">
                  <span className="font-medium text-sm break-words group-hover:text-slate-600 transition-colors">{item.account_name || "Compte sans nom"}</span>
                  <span className="text-xs text-muted-foreground">{formatRate(Number(item.percentage_of_group) || 0, 1)} du groupe</span>
                </div>
                <div className="shrink-0 text-right">
                  <span className="whitespace-nowrap font-bold text-sm tabular-nums amount-blur">{formatCurrency(item.value)}</span>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
