import { useTranslation } from "react-i18next"
import { useInvestments } from "./useInvestments"
import { InvestmentsKpis } from "./InvestmentsKpis"
import { AccountsAllocation } from "./AccountsAllocation"
import { PerformanceSection } from "./PerformanceSection"
import { AdvancedCharts } from "./AdvancedCharts"
import { TopCompanies } from "./TopCompanies"
import { EtfCompositions } from "./EtfCompositions"
import { DrillDownDialog } from "./DrillDownDialog"

export default function Investments() {
  const { t } = useTranslation("investments")
  const ctx = useInvestments()
  const { loading } = ctx
  if (loading) return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-12 w-12 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
        <p className="text-slate-500 font-medium">{t("index.chargementDeVosInvestissements")}</p>
      </div>
    </div>
  )

  return (
    <div className="space-y-8 md:space-y-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{t("index.investissements")}</h1>
        <p className="text-sm text-muted-foreground mt-1 md:text-base">{t("index.suivezLaPerformanceEtLa")}</p>
      </div>

      <InvestmentsKpis ctx={ctx} />

      <AccountsAllocation ctx={ctx} />

      <PerformanceSection ctx={ctx} />

      {/* Section 3: Analyses avancées */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">{t("index.analysesAvancees")}</h2>
          <p className="text-sm text-muted-foreground">{t("index.visionGlobaleDeVosActifs")}</p>
        </div>
        
        <AdvancedCharts ctx={ctx} />

        <TopCompanies ctx={ctx} />

        <EtfCompositions ctx={ctx} />
      </div>

      <DrillDownDialog ctx={ctx} />
    </div>
  )
}
