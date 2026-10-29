import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tag } from "lucide-react"
import { formatCurrency } from "@/lib/utils"
import type { OverviewTabCtx } from "./useOverviewTab"

/** Totaux par tag. */
export function TagTotalsCard({ ctx }: { ctx: OverviewTabCtx }) {
  const { tagTotals } = ctx
  return (
    <>
      {tagTotals.length > 0 && (
        <Card className="shadow-sm border-slate-100 overflow-hidden md:mt-8">
          <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">Projets & Contextes (Tags)</CardTitle>
              <CardDescription>Dépenses transverses sur la période.</CardDescription>
            </div>
            <Tag className="h-5 w-5 text-slate-400" />
          </CardHeader>
          <CardContent className="p-4 md:p-6">
            <div className="flex flex-wrap gap-2 md:gap-4">
              {tagTotals.map((t) => (
                <div key={t.id} className="flex items-center gap-3 p-3 px-4 bg-white border border-slate-200 rounded-full shadow-sm hover:border-slate-300 transition-colors group">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: t.color || "#64748b" }} />
                  <div>
                    <p className="text-[11px] font-medium text-slate-500 leading-none mb-1">{t.name}</p>
                    <p className="text-sm font-bold text-slate-900 leading-none">{formatCurrency(t.total_eur, "EUR")}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  )
}
