import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { formatAmountWithShare, formatCurrency } from "@/lib/utils"
import type { OverviewTabCtx } from "./useOverviewTab"

/** Camembert du patrimoine et total au centre. */
export function WealthPie({ ctx }: { ctx: OverviewTabCtx }) {
  const { chartData, chartDataKey, isMobile, patrimoineAllocation } = ctx
  return (
    <>
      {/* Camembert (PieChart) */}
      <div className="lg:col-span-5 h-[240px] md:h-[300px] flex items-center justify-center relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={isMobile ? 62 : 75}
              outerRadius={isMobile ? 85 : 100}
              paddingAngle={3}
              dataKey={chartDataKey}
              nameKey="name"
            >
              {chartData.map((item: any, i: number) => (
                <Cell key={i} fill={item.color} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} 
              formatter={(v: number) => formatAmountWithShare(v, chartData.reduce((s: number, i: any) => s + (Number(i[chartDataKey]) || 0), 0), "EUR")} 
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Center Text (Total) */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Patrimoine</span>
          <span className="text-base md:text-lg font-black text-slate-800 amount-blur">
            {formatCurrency(patrimoineAllocation.total_patrimoine, "EUR")}
          </span>
        </div>
      </div>
    </>
  )
}
