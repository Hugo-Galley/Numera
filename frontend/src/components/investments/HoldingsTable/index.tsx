import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { CostEstimateDialog } from "../CostEstimateDialog"
import { Layers, Search, SlidersHorizontal } from "lucide-react"
import { PointZeroModal } from "../PointZeroModal"
import { HoldingsTableProps } from "./types"
import { useHoldingsTable } from "./useHoldingsTable"
import { HoldingsHeader } from "./HoldingsHeader"
import { HoldingsMobileList } from "./HoldingsMobileList"
import { HoldingsDesktopTable } from "./HoldingsDesktopTable"

export function HoldingsTable({
  accountId,
  accountName,
  holdings,
  onRefresh,
  onAddDividend,
}: HoldingsTableProps) {
  const ctx = useHoldingsTable(accountId, accountName, holdings, onRefresh, onAddDividend)
  const { costEstimateOpen, filteredHoldings, hasActiveFilters, pointZeroOpen, resetFilters, setCostEstimateOpen, setPointZeroOpen } = ctx
  return (
    <>
      <Card className="shadow-sm">
        <HoldingsHeader ctx={ctx} />

        <CardContent className="p-0">
          {holdings.length === 0 ? (
            <div className="p-10 text-center space-y-3">
              <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                <Layers className="h-6 w-6" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h4 className="font-semibold text-base text-slate-900">Aucune position active renseignée</h4>
                <p className="text-sm text-slate-500">
                  Définissez votre <strong>Point Zéro</strong> en indiquant le nombre de parts détenues. Numera valorise vos positions au cours réel du marché.
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => setPointZeroOpen(true)}
                className="gap-2 mt-2"
              >
                <SlidersHorizontal className="h-4 w-4" />
                Définir l'état des lieux
              </Button>
            </div>
          ) : filteredHoldings.length === 0 ? (
            /* Empty state when filters return nothing */
            <div className="py-12 text-center">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 mb-3 text-slate-300">
                <Search className="h-5 w-5" />
              </div>
              <p className="text-slate-500 font-medium text-sm">Aucune position ne correspond aux filtres</p>
              <button
                onClick={resetFilters}
                className="mt-2 text-xs text-slate-400 hover:text-slate-600 underline underline-offset-2 transition-colors"
              >
                Réinitialiser les filtres
              </button>
            </div>
          ) : (
            <div>
              {hasActiveFilters && (
                <div className="px-4 py-2 text-xs text-slate-400 border-b bg-slate-50/50">
                  {filteredHoldings.length} résultat{filteredHoldings.length > 1 ? "s" : ""} sur {holdings.length} position{holdings.length > 1 ? "s" : ""}
                </div>
              )}

              <HoldingsMobileList ctx={ctx} />

              <HoldingsDesktopTable ctx={ctx} />
            </div>
          )}
        </CardContent>
      </Card>

      <CostEstimateDialog
        open={costEstimateOpen}
        onOpenChange={setCostEstimateOpen}
        accountId={accountId}
        onApplied={onRefresh}
      />

      <PointZeroModal
        open={pointZeroOpen}
        onOpenChange={setPointZeroOpen}
        accountId={accountId}
        accountName={accountName}
        onBaselineSaved={onRefresh}
      />
    </>
  )
}
