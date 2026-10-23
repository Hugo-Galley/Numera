import { 
  ArrowUpRight,
  ArrowDownRight,
  Wallet
} from "lucide-react"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import { AreaChart, Area, ResponsiveContainer } from "recharts"

const Sparkline = ({ data, dataKey, color }: { data: any[], dataKey: string, color: string }) => (
  <div className="h-8 sm:h-10 w-full mt-1.5 sm:mt-2">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
        <Area 
          type="monotone" 
          dataKey={dataKey} 
          stroke={color} 
          fill={color} 
          fillOpacity={0.1} 
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  </div>
)

interface DashboardKPIsProps {
  selectedAccountId: string
  displayCurrency: string
  analytics: any
  kpiHistory: any[]
}

export function DashboardKPIs({
  selectedAccountId,
  displayCurrency,
  analytics,
  kpiHistory
}: DashboardKPIsProps) {
  return (
    <div className="grid gap-3 md:gap-6 grid-cols-2 md:grid-cols-3">
      <Card className="shadow-sm border-slate-100 hover:border-emerald-200 transition-colors cursor-pointer group">
        <CardHeader className="p-3 pb-1 sm:p-6 sm:pb-2 flex flex-row items-center justify-between gap-2 space-y-0">
          <CardDescription className="text-xs sm:text-sm font-medium group-hover:text-emerald-600 transition-colors">
            {selectedAccountId === "all" ? "Revenus Mensuels" : "Entrées d'argent"}
          </CardDescription>
          <div className="hidden sm:flex h-8 w-8 bg-emerald-50 rounded-full items-center justify-center group-hover:bg-emerald-100 transition-colors">
            <ArrowUpRight className="h-4 w-4 text-emerald-600" />
          </div>
        </CardHeader>
        <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
          <CardTitle className="text-xl sm:text-2xl font-bold whitespace-nowrap tabular-nums">
            <span className="amount-blur">{formatCurrency(analytics?.revenus_totaux || 0, displayCurrency)}</span>
          </CardTitle>
          <Sparkline data={kpiHistory} dataKey="revenus" color="#10b981" />
          <p className="hidden sm:block text-[10px] text-slate-400 mt-2 uppercase tracking-wider font-bold">Tendance 6 mois</p>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 hover:border-rose-200 transition-colors cursor-pointer group">
        <CardHeader className="p-3 pb-1 sm:p-6 sm:pb-2 flex flex-row items-center justify-between gap-2 space-y-0">
          <CardDescription className="text-xs sm:text-sm font-medium group-hover:text-rose-600 transition-colors">
            {selectedAccountId === "all" ? "Dépenses Mensuelles" : "Sorties d'argent"}
          </CardDescription>
          <div className="hidden sm:flex h-8 w-8 bg-rose-50 rounded-full items-center justify-center group-hover:bg-rose-100 transition-colors">
            <ArrowDownRight className="h-4 w-4 text-rose-600" />
          </div>
        </CardHeader>
        <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
          <CardTitle className="text-xl sm:text-2xl font-bold whitespace-nowrap tabular-nums">
            <span className="amount-blur">{formatCurrency(analytics?.depenses_totales || 0, displayCurrency)}</span>
          </CardTitle>
          <Sparkline data={kpiHistory} dataKey="depenses" color="#f43f5e" />
          <p className="hidden sm:block text-[10px] text-slate-400 mt-2 uppercase tracking-wider font-bold">Tendance 6 mois</p>
        </CardContent>
      </Card>

      <Card className="col-span-2 md:col-span-1 shadow-sm border-slate-100 hover:border-blue-200 transition-colors cursor-pointer group">
        <CardHeader className="p-3 pb-1 sm:p-6 sm:pb-2 flex flex-row items-center justify-between gap-2 space-y-0">
          <CardDescription className="text-xs sm:text-sm font-medium group-hover:text-blue-600 transition-colors">
            {selectedAccountId === "all" ? "Épargne Réalisée" : "Solde Actuel"}
          </CardDescription>
          <div className="hidden sm:flex h-8 w-8 bg-blue-50 rounded-full items-center justify-center group-hover:bg-blue-100 transition-colors">
            <Wallet className="h-4 w-4 text-blue-600" />
          </div>
        </CardHeader>
        <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
          <CardTitle className="text-xl sm:text-2xl font-bold whitespace-nowrap tabular-nums">
            <span className="amount-blur">
              {formatCurrency(selectedAccountId === "all" ? analytics?.revenus_apres_depenses : analytics?.solde_actuel, displayCurrency)}
            </span>
          </CardTitle>
          <Sparkline data={kpiHistory} dataKey="epargne_flow" color="#3b82f6" />
          <p className="hidden sm:block text-[10px] text-slate-400 mt-2 uppercase tracking-wider font-bold">Tendance 6 mois</p>
        </CardContent>
      </Card>
    </div>
  )
}

