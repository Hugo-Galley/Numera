import i18n from "i18next"
import { useTranslation } from "react-i18next"
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
  const { t } = useTranslation("investments")
  const ctx = useHoldingsTable(accountId, accountName, holdings, onRefresh, onAddDividend)
  const { costEstimateOpen, filteredHoldings, hasActiveFilters, pointZeroOpen, resetFilters, setCostEstimateOpen, setPointZeroOpen } = ctx
  return (
    <>
      <Card className="shadow-xs">
        <HoldingsHeader ctx={ctx} />

        <CardContent className="p-0">
          {holdings.length === 0 ? (
            <div className="p-10 text-center space-y-3">
              <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                <Layers className="h-6 w-6" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h4 className="font-semibold text-base text-slate-900">{t("index.aucunePositionActiveRenseignee")}</h4>
                <p className="text-sm text-slate-500">
                  {t("index.definissezVotre")} <strong>{t("index.pointZero")}</strong> {t("index.enIndiquantLeNombreDe")}
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => setPointZeroOpen(true)}
                className="gap-2 mt-2"
              >
                <SlidersHorizontal className="h-4 w-4" />
                {t("index.definirLEtatDesLieux")}
              </Button>
            </div>
          ) : filteredHoldings.length === 0 ? (
            /* Empty state when filters return nothing */
            <div className="py-12 text-center">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 mb-3 text-slate-300">
                <Search className="h-5 w-5" />
              </div>
              <p className="text-slate-500 font-medium text-sm">{t("index.aucunePositionNeCorrespondAux")}</p>
              <button
                onClick={resetFilters}
                className="mt-2 text-xs text-slate-400 hover:text-slate-600 underline underline-offset-2 transition-colors"
              >
                {t("index.reinitialiserLesFiltres")}
              </button>
            </div>
          ) : (
            <div>
              {hasActiveFilters && (
                <div className="px-4 py-2 text-xs text-slate-400 border-b bg-slate-50/50">
                  {i18n.t("misc.resultsOf", { ns: "investments", results: i18n.t("misc.results", { ns: "investments", count: filteredHoldings.length }), positions: i18n.t("misc.positions", { ns: "investments", count: holdings.length }) })}
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
