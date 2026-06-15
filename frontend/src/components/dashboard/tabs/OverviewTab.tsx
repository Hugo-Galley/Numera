import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { Tag } from "lucide-react"
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine
} from "recharts"
import { SankeyFlow } from "@/components/analytics/SankeyFlow"
import { formatCurrency } from "@/lib/utils"
import { IconComponent } from "../IconComponent"

const COLORS = ["#3b82f6", "#10b981", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#f59e0b", "#64748b"]

interface OverviewTabProps {
  sankeyData: any
  expensesByCategory: any[]
  displayCurrency: string
  tagTotals: any[]
}

export function OverviewTab({
  sankeyData,
  expensesByCategory,
  displayCurrency,
  tagTotals
}: OverviewTabProps) {
  return (
    <div className="space-y-8">
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <CardTitle className="text-lg">Flux Financiers</CardTitle>
          <CardDescription>Visualisation des revenus vers les dépenses et l'épargne.</CardDescription>
        </CardHeader>
        <CardContent className="p-6 h-[600px]">
          <SankeyFlow data={sankeyData} currency={displayCurrency} />
        </CardContent>
      </Card>

      <div className="grid gap-8 lg:grid-cols-12">
        <Card className="lg:col-span-8 shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b pb-4">
            <CardTitle className="text-lg">Dépenses par catégorie</CardTitle>
            <CardDescription>Où va votre argent ce mois-ci ?</CardDescription>
          </CardHeader>
          <CardContent className="p-0 sm:p-6 h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={expensesByCategory} layout="vertical" margin={{ top: 40, right: 40, left: 40, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis type="number" hide />
                <YAxis dataKey="category.name" type="category" width={100} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
                <Bar dataKey="total" radius={[0, 4, 4, 0]} barSize={20}>
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
          <CardHeader className="bg-slate-50/50 border-b pb-4">
            <CardTitle className="text-lg">Répartition</CardTitle>
            <CardDescription>Poids des catégories.</CardDescription>
          </CardHeader>
          <CardContent className="p-6 flex flex-col items-center">
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                  <Pie data={expensesByCategory} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={4} dataKey="total" nameKey="category.name">
                    {expensesByCategory.map((item, i) => <Cell key={i} fill={item.category.color || COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="w-full space-y-3 mt-4">
               {expensesByCategory.slice(0, 4).map((item, i) => (
                 <div key={i} className="flex justify-between text-sm">
                   <span className="text-slate-500 flex items-center gap-2">
                     <div className="h-4 w-4 rounded-lg flex items-center justify-center" style={{ backgroundColor: item.category.color || COLORS[i % COLORS.length] }}>
                       <IconComponent name={item.category.icon} className="h-2 w-2 text-white" />
                     </div>
                     {item.category.name}
                   </span>
                   <span className="font-bold">
                     <span className="amount-blur">{item.percentage}%</span>
                   </span>
                 </div>
               ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {tagTotals.length > 0 && (
        <Card className="shadow-sm border-slate-100 overflow-hidden mt-8">
          <CardHeader className="bg-slate-50/50 border-b pb-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">Projets & Contextes (Tags)</CardTitle>
              <CardDescription>Dépenses transverses sur la période.</CardDescription>
            </div>
            <Tag className="h-5 w-5 text-slate-400" />
          </CardHeader>
          <CardContent className="p-6">
            <div className="flex flex-wrap gap-4">
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
    </div>
  )
}
