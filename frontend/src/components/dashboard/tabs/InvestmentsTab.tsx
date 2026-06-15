import { TrendingUp, PieChart as PieChartIcon } from "lucide-react"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell
} from "recharts"

const COLORS = ["#3b82f6", "#10b981", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#f59e0b", "#64748b"]

interface InvestmentsTabProps {
  investments: any
  allocation: any
  displayCurrency: string
  onInvestmentBarClick: (data: any) => void
  onAllocationClick: (_: any, index: number) => void
}

export function InvestmentsTab({
  investments,
  allocation,
  displayCurrency,
  onInvestmentBarClick,
  onAllocationClick
}: InvestmentsTabProps) {
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Versements du mois</CardTitle>
          </div>
          <CardDescription>Par compte d'investissement.</CardDescription>
        </CardHeader>
        <CardContent className="p-0 sm:p-6 h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart 
              data={investments?.items || []} 
              layout="vertical" 
              margin={{ top: 40, right: 50, left: 50, bottom: 20 }}
              onClick={(state: any) => {
                if (state && state.activePayload && state.activePayload.length > 0) {
                  onInvestmentBarClick(state.activePayload[0].payload)
                }
              }}
              className="cursor-pointer"
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis type="number" hide />
              <YAxis dataKey="account_name" type="category" width={150} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip cursor={{ fill: '#f8fafc' }} formatter={(v: number) => formatCurrency(v, displayCurrency)} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
              <Bar dataKey="total_verse" name="Versement" fill="#0f172a" radius={[0, 4, 4, 0]} barSize={30} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <div className="flex items-center gap-2">
            <PieChartIcon className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Répartition Patrimoine</CardTitle>
          </div>
          <CardDescription>Part de chaque compte investi.</CardDescription>
        </CardHeader>
        <CardContent className="p-6 h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
              <Pie 
                data={allocation?.items || []} 
                cx="50%" 
                cy="50%" 
                innerRadius={80} 
                outerRadius={110} 
                paddingAngle={4} 
                dataKey="current_value" 
                nameKey="account_name"
                onClick={onAllocationClick}
                className="cursor-pointer"
              >
                {allocation?.items?.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
