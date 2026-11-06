import { useTranslation } from "react-i18next"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { SankeyFlow } from "@/components/analytics/SankeyFlow"
import type { OverviewTabCtx } from "./useOverviewTab"

/** Flux d'argent (Sankey). */
export function SankeyCard({ ctx }: { ctx: OverviewTabCtx }) {
  const { t } = useTranslation("dashboard")
  const { displayCurrency, drilldownScope, isMobile, openDrilldown, sankeyData } = ctx
  return (
    <>
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
          <CardTitle className="text-lg">{t("overview.flowTitle")}</CardTitle>
          <CardDescription>{t("overview.flowSubtitle")}</CardDescription>
        </CardHeader>
        <CardContent className="p-3 md:p-6">
          {isMobile ? (
            // Mobile : même diagramme que sur PC, calculé sur une largeur lisible et défilant au doigt
            <div>
              <div className="-mx-1 overflow-x-auto overscroll-x-contain pb-2">
                <div className="min-w-[640px]">
                  <SankeyFlow data={sankeyData} currency={displayCurrency} onCategoryClick={(categoryId, label) => openDrilldown({ ...drilldownScope, label, categoryId })} />
                </div>
              </div>
              <p className="mt-1 text-center text-xs text-slate-400">{t("overview.dragHint")}</p>
            </div>
          ) : (
            <SankeyFlow data={sankeyData} currency={displayCurrency} onCategoryClick={(categoryId, label) => openDrilldown({ ...drilldownScope, label, categoryId })} />
          )}
        </CardContent>
      </Card>
    </>
  )
}
