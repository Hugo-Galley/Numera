import { useTranslation } from "react-i18next"
import { AllocationTreemap } from "@/components/analytics/AllocationTreemap"
import { Info } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { categoryColor, UNCLASSIFIED_NAME } from "@/lib/chartPalette"
import { formatRate } from "@/lib/utils"
import type { InvestmentsCtx } from "./useInvestments"

/** Classes d'actifs en treemap ; un clic ouvre le détail par compte. Secteurs et pays : onglet Exposition. */
export function AssetClassTreemap({ ctx }: { ctx: InvestmentsCtx }) {
  const { t } = useTranslation("investments")
  const { advancedAllocation, getDrilldownItems, getDrilldownTitle, setDrillDown } = ctx
  return (
      <Card className="shadow-xs">
        <CardHeader className="flex flex-row items-center justify-between gap-2 pb-2 border-b">
          <CardTitle className="text-base font-bold">{t("advancedCharts.parClasseDActif")}</CardTitle>
        </CardHeader>
        <CardContent className="px-3 pt-4 md:px-6 md:pt-6">
          {advancedAllocation ? (
            <>
            <AllocationTreemap 
              data={advancedAllocation.by_asset_class} 
              onItemClick={(node) => setDrillDown({ title: getDrilldownTitle("Classe d'actif", node), items: getDrilldownItems(node) })}
            />
            {/* Légende : les petites classes n'ont pas la place d'afficher leur nom dans le treemap */}
            <ul className="mt-4 grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
              {advancedAllocation.by_asset_class.map((item, i) => (
                <li key={item.name}>
                  <button
                    type="button"
                    className="flex min-h-10 w-full items-center justify-between gap-2 rounded-md px-2 text-xs hover:bg-slate-50 md:min-h-8"
                    onClick={() => setDrillDown({ title: getDrilldownTitle("Classe d'actif", item), items: getDrilldownItems(item) })}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: categoryColor(i, item.name) }} />
                      <span className="truncate" title={item.name}>{item.name}</span>
                    </span>
                    <span className="shrink-0 font-bold tabular-nums">{formatRate(item.percentage, 1)}</span>
                  </button>
                </li>
              ))}
            </ul>
            {advancedAllocation.by_asset_class.some((g) => g.name === UNCLASSIFIED_NAME) && (
              <p className="mt-3 flex items-start gap-1.5 text-xs text-slate-500">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" aria-hidden />
                {t("advancedCharts.nonClasseAide")}
              </p>
            )}
            </>
          ) : (
            <div className="h-[400px] flex items-center justify-center">
              <div className="h-8 w-8 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
            </div>
          )}
        </CardContent>
      </Card>
  )
}
