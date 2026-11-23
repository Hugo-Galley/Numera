import { useTranslation } from "react-i18next"
import { Info } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { SankeyFlow } from "@/components/analytics/SankeyFlow"
import { SankeyList } from "@/components/analytics/SankeyList"
import type { OverviewTabCtx } from "./useOverviewTab"

/** Flux d'argent (Sankey) ; en liste sur mobile, où le diagramme ne tenait pas dans la largeur. */
export function SankeyCard({ ctx, incomePending = false }: { ctx: OverviewTabCtx; incomePending?: boolean }) {
  const { t } = useTranslation("dashboard")
  const { displayCurrency, drilldownScope, isMobile, openDrilldown, sankeyData } = ctx
  const onCategoryClick = (categoryId: number, label: string) => openDrilldown({ ...drilldownScope, label, categoryId })
  return (
    <Card className="shadow-xs border-slate-100 overflow-hidden">
      <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
        <CardTitle className="text-lg">{t("overview.flowTitle")}</CardTitle>
        <CardDescription>{t("overview.flowSubtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="p-3 md:p-6">
        {incomePending && (
          // Mois en cours sans revenu encore reçu : la source « Déficit / Trésorerie » n'est pas un vrai déficit
          <p className="mb-3 flex items-start gap-2 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900 md:mb-4">
            <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{t("overview.incomePending")}</span>
          </p>
        )}
        {isMobile ? (
          <SankeyList data={sankeyData} currency={displayCurrency} onCategoryClick={onCategoryClick} />
        ) : (
          <SankeyFlow data={sankeyData} currency={displayCurrency} onCategoryClick={onCategoryClick} />
        )}
      </CardContent>
    </Card>
  )
}
