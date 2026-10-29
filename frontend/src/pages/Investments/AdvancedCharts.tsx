import { AllocationTreemap } from "@/components/analytics/AllocationTreemap"
import { Badge } from "@/components/ui/badge"
import { Briefcase, Layers } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { formatAmountWithShare, formatRate } from "@/lib/utils"
import { COLORS } from "./types"
import type { InvestmentsCtx } from "./useInvestments"

/** Analyses avancées : treemap, carte et répartitions. */
export function AdvancedCharts({ ctx }: { ctx: InvestmentsCtx }) {
  const { advancedAllocation, allocation, diversity, getDrilldownItems, getDrilldownTitle, setDrillDown } = ctx
  return (
    <>
      <Card className="shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between gap-2 pb-2 border-b">
          <div>
            <CardTitle className="text-base font-bold">Vue d'ensemble de l'allocation</CardTitle>
          </div>
          <Badge variant="secondary" className="bg-slate-100 text-slate-900 pointer-events-none shadow-none border-none">Treemap</Badge>
        </CardHeader>
        <CardContent className="px-3 pt-4 md:px-6 md:pt-6">
          {advancedAllocation ? (
            <AllocationTreemap 
              data={advancedAllocation.by_asset_class} 
              onItemClick={(node) => setDrillDown({ title: getDrilldownTitle("Classe d'actif", node), items: getDrilldownItems(node) })}
            />
          ) : (
            <div className="h-[400px] flex items-center justify-center">
              <div className="h-8 w-8 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:gap-6 grid-cols-1 md:grid-cols-2">
        <Card className="shadow-sm">
          <CardHeader className="border-b pb-3">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-slate-500" />
              <CardTitle className="text-base">Par Classe d'actif</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-5 flex flex-col items-center">
            <div className="h-[190px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                  <Pie
                    data={advancedAllocation?.by_asset_class || []}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={4}
                    dataKey="value"
                    nameKey="name"
                    onClick={(data) => setDrillDown({ title: getDrilldownTitle("Classe d'actif", data), items: getDrilldownItems(data) })}
                    className="cursor-pointer outline-none"
                  >
                    {(advancedAllocation?.by_asset_class || []).map((_: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => formatAmountWithShare(value, (advancedAllocation?.by_asset_class || []).reduce((s: number, i: any) => s + (i.value || 0), 0))} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="w-full space-y-1.5 mt-3 px-2">
              {(advancedAllocation?.by_asset_class || []).slice(0, 4).map((item: any, i: number) => (
                <div 
                  key={i} 
                  className="flex min-h-9 items-center justify-between gap-2 text-xs cursor-pointer hover:text-slate-600 transition-colors md:min-h-0"
                  onClick={() => setDrillDown({ title: `Classe d'actif : ${item.name}`, items: item.items || [] })}
                >
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                    <span className="truncate max-w-[200px] md:max-w-[150px]">{item.name}</span>
                  </div>
                  <span className="font-bold shrink-0">{item.percentage}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="border-b pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-slate-500" />
                <CardTitle className="text-base">Par Secteur</CardTitle>
              </div>
              {diversity && diversity.sectors.length > 0 && (
                <Badge variant="secondary" className="bg-slate-100 text-slate-600 text-[10px] pointer-events-none shadow-none border-none">Look-Through</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-5 flex flex-col items-center">
            {(() => {
              const sectorData = diversity && diversity.sectors.length > 0
                ? diversity.sectors.map(s => ({ name: s.name, value: s.value_eur, percentage: s.percentage_stocks }))
                : (advancedAllocation?.by_sector || [])
              return (
                <>
                  <div className="h-[190px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                        <Pie
                          data={sectorData}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={75}
                          paddingAngle={4}
                          dataKey="value"
                          nameKey="name"
                          className="outline-none"
                        >
                          {sectorData.map((_: any, index: number) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value: number) => formatAmountWithShare(value, sectorData.reduce((s: number, i: any) => s + (i.value || 0), 0))} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="w-full space-y-1.5 mt-3 px-2">
                    {sectorData.slice(0, 4).map((item: any, i: number) => (
                      <div 
                        key={i} 
                        className="flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                          <span className="truncate max-w-[200px] md:max-w-[150px]">{item.name}</span>
                        </div>
                        <span className="font-bold shrink-0">{typeof item.percentage === 'number' ? formatRate(item.percentage, 1) : `${item.percentage}\u00a0%`}</span>
                      </div>
                    ))}
                  </div>
                </>
              )
            })()}
          </CardContent>
        </Card>
      </div>
    </>
  )
}
