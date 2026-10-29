import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { formatCurrency } from "@/lib/utils"
import type { OverviewTabCtx } from "./useOverviewTab"
import { WealthPie } from "./WealthPie"
import { WealthDetails } from "./WealthDetails"

/** Répartition du patrimoine. */
export function WealthAllocationCard({ ctx }: { ctx: OverviewTabCtx }) {
  const { groupBy, patrimoineAllocation, setGroupBy } = ctx
  return (
    <>
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3 md:gap-4">
          <div>
            <CardTitle className="text-lg">Répartition du Patrimoine</CardTitle>
            <CardDescription>
              Distribution de vos actifs sur l'ensemble de vos comptes actifs.
            </CardDescription>
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-3 md:gap-4 self-stretch md:self-auto">
            {/* View Mode Toggle */}
            <Tabs value={groupBy} onValueChange={(v) => setGroupBy(v as any)} className="w-full md:w-auto min-w-0">
              <TabsList className="bg-slate-100 border border-slate-200/50 p-1 rounded-xl w-full md:w-auto overflow-x-auto justify-start [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                <TabsTrigger value="category" className="rounded-lg text-xs font-semibold px-3 py-1">Par Catégorie</TabsTrigger>
                <TabsTrigger value="mixed" className="rounded-lg text-xs font-semibold px-3 py-1">Mixte</TabsTrigger>
                <TabsTrigger value="account" className="rounded-lg text-xs font-semibold px-3 py-1">Par Compte</TabsTrigger>
                <TabsTrigger value="institution" className="rounded-lg text-xs font-semibold px-3 py-1">Par Établissement</TabsTrigger>
              </TabsList>
            </Tabs>
            <span className="text-sm font-semibold text-slate-500 bg-slate-100/80 px-3 py-1 rounded-lg whitespace-nowrap">
              Total : <span className="amount-blur text-slate-900 font-bold">{formatCurrency(patrimoineAllocation?.total_patrimoine || 0, "EUR")}</span>
            </span>
            {patrimoineAllocation?.total_debts_eur > 0 && (
              <span className="text-sm font-semibold text-slate-500 bg-slate-100/80 px-3 py-1 rounded-lg whitespace-nowrap">
                Dettes : <span className="text-rose-600 font-bold">−{formatCurrency(patrimoineAllocation.total_debts_eur, "EUR")}</span>
                {" · "}Net : <span className="text-slate-900 font-bold">{formatCurrency(patrimoineAllocation.net_patrimoine_eur, "EUR")}</span>
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-4 md:p-6">
          {(!patrimoineAllocation || !patrimoineAllocation.items || patrimoineAllocation.items.length === 0) ? (
            <div className="text-center py-8 text-slate-400">Aucune donnée de patrimoine disponible.</div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:gap-8 lg:grid-cols-12 items-center">
              <WealthPie ctx={ctx} />

              <WealthDetails ctx={ctx} />
            </div>
          )}
        </CardContent>
      </Card>
    </>
  )
}
