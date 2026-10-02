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
        <CardContent className="p-6 h-[400px] flex items-center justify-center relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
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
          {/* Center Text (Total) */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total</span>
            <span className="text-lg font-black text-slate-800 amount-blur">
              {formatCurrency(allocation?.total_current_value || 0, displayCurrency)}
            </span>
            <span className="text-[11px] text-muted-foreground font-medium">
              {allocation?.items?.length || 0} {allocation?.items?.length > 1 ? "comptes" : "compte"}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
