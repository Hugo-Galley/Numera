import { Badge } from "@/components/ui/badge"
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Building } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { InvestmentsCtx } from "./useInvestments"

/** Top 10 des entreprises en transparence. */
export function TopCompanies({ ctx }: { ctx: InvestmentsCtx }) {
  const { diversity, isMobile } = ctx
  return (
    <>
      {/* Top 10 Companies Look-Through */}
      {diversity && diversity.top_underlying_companies.length > 0 && (
        <Card className="shadow-sm">
          <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b gap-2">
            <div>
              <div className="flex items-center gap-2">
                <Building className="h-4 w-4 text-slate-500" />
                <CardTitle className="text-base font-bold">Top 10 Entreprises Détenues (Look-Through)</CardTitle>
              </div>
              <CardDescription className="text-xs mt-0.5">
                Exposition consolidée : direct + sous-jacents de vos ETFs.
              </CardDescription>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-slate-900" /> Direct
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-slate-400" /> Via ETFs
              </span>
            </div>
          </CardHeader>
          <CardContent className="px-2 pt-4 md:px-6 md:pt-6">
            {(() => {
              const topCompaniesData = diversity.top_underlying_companies.slice(0, 10).map((c) => {
                const total = c.total_value_eur || (c.direct_value_eur + c.indirect_value_eur)
                return {
                  name: c.name,
                  ticker: c.ticker,
                  direct: c.direct_value_eur,
                  indirect: c.indirect_value_eur,
                  total: total,
                  pct: c.pct_stocks,
                  sources: c.sources,
                  has_overlap: c.has_overlap,
                }
              })

              return (
                <div className="h-[340px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={topCompaniesData}
                      layout="vertical"
                      margin={{ top: 5, right: isMobile ? 8 : 30, left: isMobile ? 0 : 15, bottom: 5 }}
                    >
                      <XAxis
                        type="number"
                        tickFormatter={(v) => `${v.toFixed(0)}€`}
                        tick={{ fontSize: 10 }}
                        tickCount={isMobile ? 3 : 5}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={(tickProps: any) => {
                          const { x, y, payload } = tickProps
                          const comp = topCompaniesData.find((c) => c.name === payload.value)
                          return (
                            <g transform={`translate(${x},${y})`}>
                              <foreignObject x={isMobile ? -105 : -135} y={-10} width={isMobile ? 100 : 130} height={20}>
                                <div
                                  className="flex items-center justify-end gap-1.5 h-full pr-1 overflow-hidden"
                                  title={payload.value}
                                >
                                  <CompanyLogo
                                    ticker={comp?.ticker}
                                    name={payload.value}
                                    className="h-4 w-4 rounded-xs shrink-0"
                                  />
                                  <span className="text-[11px] font-medium text-slate-700 truncate max-w-[75px] md:max-w-[105px]">
                                    {payload.value}
                                  </span>
                                </div>
                              </foreignObject>
                            </g>
                          )
                        }}
                        axisLine={false}
                        tickLine={false}
                        width={isMobile ? 110 : 140}
                      />
                      <Tooltip
                        cursor={false}
                        content={({ active, payload, label }: any) => {
                          if (active && payload && payload.length) {
                            const d = payload[0].payload
                            return (
                              <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-md text-xs space-y-1.5 min-w-[210px]">
                                <div className="flex items-center justify-between border-b pb-1.5 gap-2">
                                  <div className="flex items-center gap-2.5 min-w-0">
                                    <CompanyLogo
                                      ticker={d.ticker}
                                      name={label || d.name}
                                      className="h-6 w-6 rounded-md shadow-2xs shrink-0"
                                    />
                                    <div className="flex flex-col min-w-0">
                                      <span className="font-bold text-slate-900 truncate">{label || d.name}</span>
                                      {d.ticker && (
                                        <span className="text-[10px] text-slate-400 font-mono font-medium">{d.ticker}</span>
                                      )}
                                    </div>
                                  </div>
                                  {d.has_overlap && (
                                    <Badge variant="outline" className="text-[9px] px-1 py-0 font-normal shrink-0">
                                      Doublon
                                    </Badge>
                                  )}
                                </div>
                                <div className="flex justify-between items-center text-slate-900 font-bold">
                                  <span>Apport total :</span>
                                  <span>{formatCurrency(d.total)} ({formatRate(d.pct, 1)})</span>
                                </div>
                                <div className="text-[11px] text-muted-foreground space-y-0.5 pt-1 border-t">
                                  <div className="flex justify-between">
                                    <span className="flex items-center gap-1.5">
                                      <span className="h-2 w-2 rounded-full bg-slate-900 shrink-0" /> Détenu en direct :
                                    </span>
                                    <span className="font-medium text-slate-700">{formatCurrency(d.direct)}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="flex items-center gap-1.5">
                                      <span className="h-2 w-2 rounded-full bg-slate-400 shrink-0" /> Détenu via ETFs :
                                    </span>
                                    <span className="font-medium text-slate-700">{formatCurrency(d.indirect)}</span>
                                  </div>
                                </div>
                              </div>
                            )
                          }
                          return null
                        }}
                      />
                      <Bar dataKey="direct" stackId="a" fill="#000000" radius={[0, 0, 0, 0]} />
                      <Bar dataKey="indirect" stackId="a" fill="#9ca3af" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )
            })()}
          </CardContent>
        </Card>
      )}
    </>
  )
}
