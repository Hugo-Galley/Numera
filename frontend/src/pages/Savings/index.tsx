import { ErrorState } from "@/components/layout/ErrorState"
import { ProvisionsSection } from "@/components/savings/ProvisionsSection"
import { useSavings } from "./useSavings"
import { SavingsHeader } from "./SavingsHeader"
import { BalanceSection } from "./BalanceSection"
import { FlowsSection } from "./FlowsSection"
import { GoalsHeader } from "./GoalsHeader"
import { GoalsGrid } from "./GoalsGrid"

export default function Savings() {
  const ctx = useSavings()
  const { loadData, loadFailed, loading, setLoadFailed } = ctx
  return (
    <div className="space-y-8 pb-10 md:space-y-12">
      <SavingsHeader ctx={ctx} />

      {loadFailed && !loading ? (
        <ErrorState message="Les données d'épargne n'ont pas pu être chargées." onRetry={() => { setLoadFailed(false); loadData() }} />
      ) : loading ? (
        <div className="flex items-center justify-center h-[400px]">
           <div className="flex flex-col items-center gap-4">
             <div className="h-10 w-10 border-4 border-slate-200 border-t-slate-900 rounded-full animate-spin" />
             <p className="text-slate-500 font-medium">Analyse en cours...</p>
           </div>
        </div>
      ) : (
        <div className="space-y-8 md:space-y-12">

          <BalanceSection ctx={ctx} />

          <FlowsSection ctx={ctx} />

          <ProvisionsSection />

          {/* SECTION 3 : OBJECTIFS */}
          <section className="space-y-4 md:space-y-6">
            <GoalsHeader ctx={ctx} />

            <GoalsGrid ctx={ctx} />
          </section>

        </div>
      )}
    </div>
  )
}
