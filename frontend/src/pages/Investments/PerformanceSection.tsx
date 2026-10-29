import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent } from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import type { InvestmentsCtx } from "./useInvestments"

/** Section 2 : performance détaillée. */
export function PerformanceSection({ ctx }: { ctx: InvestmentsCtx }) {
  const { chartData, handleAccountClick, isMobile } = ctx
  return (
    <>
      {/* Section 2: Performance détaillée */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Performance détaillée</h2>
          <p className="text-sm text-muted-foreground">Historique et évolution de vos supports.</p>
        </div>
        <Card className="shadow-sm">
          <CardContent className="h-[260px] px-2 sm:px-6 pt-6 md:h-[300px]">
             <ResponsiveContainer width="100%" height="100%">
               <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                 <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                 <XAxis 
                   dataKey="name" 
                   axisLine={false} 
                   tickLine={false} 
                   tick={{ fontSize: 10 }}
                   interval={0}
                   angle={-45}
                   textAnchor="end"
                   height={isMobile ? 70 : 60}
                   tickFormatter={(v: string) => (isMobile && v.length > 12 ? `${v.slice(0, 11)}…` : v)}
                 />
                 <YAxis 
                   axisLine={false} 
                   tickLine={false} 
                   tick={{ fontSize: 10 }}
                   tickFormatter={(v) => `${v}€`} 
                 />
                 <Tooltip 
                    formatter={(value: number, name: string) => [formatCurrency(value), name]}
                    contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0" }}
                 />
                 <Bar 
                   dataKey="value" 
                   fill="#000000" 
                   radius={[4, 4, 0, 0]} 
                   onClick={(data) => handleAccountClick(data.id)}
                   className="cursor-pointer hover:opacity-80 transition-opacity"
                 />
               </BarChart>
             </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
