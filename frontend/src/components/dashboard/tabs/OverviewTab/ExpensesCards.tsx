import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { IconComponent } from "../../IconComponent"
import { formatAmountWithShare, formatRate } from "@/lib/utils"
import { COLORS } from "./types"
import type { OverviewTabCtx } from "./useOverviewTab"

/** Dépenses par catégorie (graphique et liste). */
export function ExpensesCards({ ctx }: { ctx: OverviewTabCtx }) {
  const { displayCurrency, expensesByCategory, isMobile, openCategory } = ctx
  return (
    <>
      <div className="grid grid-cols-1 gap-5 md:gap-8 lg:grid-cols-12">
        <Card className="lg:col-span-8 shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
            <CardTitle className="text-lg">Dépenses par catégorie</CardTitle>
            <CardDescription>Où va votre argent ce mois-ci ? Cliquez sur une barre pour voir les transactions.</CardDescription>
          </CardHeader>
          <CardContent className="p-2 sm:p-6" style={{ height: isMobile ? Math.max(220, expensesByCategory.length * 34 + 30) : 400 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={expensesByCategory} layout="vertical" margin={isMobile ? { top: 8, right: 16, left: 0, bottom: 8 } : { top: 40, right: 40, left: 40, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis type="number" hide />
                <YAxis dataKey="category.name" type="category" width={isMobile ? 92 : 100} axisLine={false} tickLine={false} tick={{ fontSize: isMobile ? 11 : 12, fill: '#64748b' }} />
                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatAmountWithShare(v, expensesByCategory.reduce((s, i) => s + (i.total || 0), 0), displayCurrency)} />
                <Bar dataKey="total" radius={[0, 4, 4, 0]} barSize={isMobile ? 16 : 20} className="cursor-pointer" onClick={(data: any) => openCategory(data?.payload ?? data)}>
                  {expensesByCategory.map((item, i) => (
                    <Cell key={i} fill={item.category.color || COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
                {expensesByCategory
                  .filter(item => item.category?.monthly_limit != null)
                  .map((item, i) => (
                    <ReferenceLine
                      key={`limit-${i}`}
                      x={item.category.monthly_limit}
                      yAxisId={0}
                      stroke="#f59e0b"
                      strokeDasharray="4 3"
                      strokeWidth={1.5}
                    />
                  ))}
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="lg:col-span-4 shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
            <CardTitle className="text-lg">Répartition</CardTitle>
            <CardDescription>Poids des catégories.</CardDescription>
          </CardHeader>
          <CardContent className="p-4 md:p-6 flex flex-col items-center">
            <div className="h-[220px] md:h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                  <Pie data={expensesByCategory} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={4} dataKey="total" nameKey="category.name">
                    {expensesByCategory.map((item, i) => <Cell key={i} fill={item.category.color || COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatAmountWithShare(v, expensesByCategory.reduce((s, i) => s + (i.total || 0), 0), displayCurrency)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="w-full space-y-3 mt-2 md:mt-4">
               {expensesByCategory.slice(0, 4).map((item, i) => (
                 <div key={i} className="flex justify-between text-sm">
                   <span className="min-w-0 truncate text-slate-500 flex items-center gap-2">
                     <div className="h-4 w-4 shrink-0 rounded-lg flex items-center justify-center" style={{ backgroundColor: item.category.color || COLORS[i % COLORS.length] }}>
                       <IconComponent name={item.category.icon} className="h-2 w-2 text-white" />
                     </div>
                     {item.category.name}
                   </span>
                   <span className="font-bold">
                     <span className="amount-blur">{formatRate(item.percentage, 1)}</span>
                   </span>
                 </div>
               ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
