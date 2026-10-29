import { useInvestments } from "./useInvestments"
import { InvestmentsKpis } from "./InvestmentsKpis"
import { AccountsAllocation } from "./AccountsAllocation"
import { PerformanceSection } from "./PerformanceSection"
import { AdvancedCharts } from "./AdvancedCharts"
import { TopCompanies } from "./TopCompanies"
import { EtfCompositions } from "./EtfCompositions"
import { DrillDownDialog } from "./DrillDownDialog"

export default function Investments() {
  const ctx = useInvestments()
  const { loading } = ctx
  if (loading) return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-12 w-12 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
        <p className="text-slate-500 font-medium">Chargement de vos investissements...</p>
      </div>
    </div>
  )

  return (
    <div className="space-y-8 md:space-y-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Investissements</h1>
        <p className="text-sm text-muted-foreground mt-1 md:text-base">Suivez la performance et la répartition de votre patrimoine investi.</p>
      </div>

      <InvestmentsKpis ctx={ctx} />

      <AccountsAllocation ctx={ctx} />

      <PerformanceSection ctx={ctx} />

      {/* Section 3: Analyses avancées */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Analyses avancées</h2>
          <p className="text-sm text-muted-foreground">Vision globale de vos actifs sous-jacents (tous comptes confondus).</p>
        </div>
        
        <AdvancedCharts ctx={ctx} />

        <TopCompanies ctx={ctx} />

        <EtfCompositions ctx={ctx} />
      </div>

      <DrillDownDialog ctx={ctx} />
    </div>
  )
}
