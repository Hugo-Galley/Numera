import { 
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Wallet
} from "lucide-react"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatCurrency } from "@/lib/utils"
import { AreaChart, Area, ResponsiveContainer } from "recharts"

const Sparkline = ({ data, dataKey, color }: { data: any[], dataKey: string, color: string }) => (
  <div className="h-10 w-full mt-2">
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
    <div className="grid gap-4 md:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
      <Card className="shadow-sm border-slate-100 hover:border-emerald-200 transition-colors cursor-pointer group">
        <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
          <CardDescription className="font-medium group-hover:text-emerald-600 transition-colors">
            {selectedAccountId === "all" ? "Revenus Mensuels" : "Entrées d'argent"}
          </CardDescription>
          <div className="h-8 w-8 bg-emerald-50 rounded-full flex items-center justify-center group-hover:bg-emerald-100 transition-colors">
            <ArrowUpRight className="h-4 w-4 text-emerald-600" />
          </div>
        </CardHeader>
        <CardContent>
          <CardTitle className="text-2xl font-bold">
            <span className="amount-blur">{formatCurrency(analytics?.revenus_totaux || 0, displayCurrency)}</span>
          </CardTitle>
          <Sparkline data={kpiHistory} dataKey="revenus" color="#10b981" />
          <p className="text-[10px] text-slate-400 mt-2 uppercase tracking-wider font-bold">Tendance 6 mois</p>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 hover:border-rose-200 transition-colors cursor-pointer group">
        <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
          <CardDescription className="font-medium group-hover:text-rose-600 transition-colors">
            {selectedAccountId === "all" ? "Dépenses Mensuelles" : "Sorties d'argent"}
          </CardDescription>
          <div className="h-8 w-8 bg-rose-50 rounded-full flex items-center justify-center group-hover:bg-rose-100 transition-colors">
            <ArrowDownRight className="h-4 w-4 text-rose-600" />
          </div>
        </CardHeader>
        <CardContent>
          <CardTitle className="text-2xl font-bold">
            <span className="amount-blur">{formatCurrency(analytics?.depenses_totales || 0, displayCurrency)}</span>
          </CardTitle>
          <Sparkline data={kpiHistory} dataKey="depenses" color="#f43f5e" />
          <p className="text-[10px] text-slate-400 mt-2 uppercase tracking-wider font-bold">Tendance 6 mois</p>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 hover:border-blue-200 transition-colors cursor-pointer group">
        <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
          <CardDescription className="font-medium group-hover:text-blue-600 transition-colors">
            {selectedAccountId === "all" ? "Épargne Réalisée" : "Solde Actuel"}
          </CardDescription>
          <div className="h-8 w-8 bg-blue-50 rounded-full flex items-center justify-center group-hover:bg-blue-100 transition-colors">
            <Wallet className="h-4 w-4 text-blue-600" />
          </div>
        </CardHeader>
        <CardContent>
          <CardTitle className="text-2xl font-bold">
            <span className="amount-blur">
              {formatCurrency(selectedAccountId === "all" ? analytics?.revenus_apres_depenses : analytics?.solde_actuel, displayCurrency)}
            </span>
          </CardTitle>
          <Sparkline data={kpiHistory} dataKey="epargne_flow" color="#3b82f6" />
          <p className="text-[10px] text-slate-400 mt-2 uppercase tracking-wider font-bold">Tendance 6 mois</p>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 hover:border-slate-300 transition-colors cursor-pointer group">
        <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
          <CardDescription className="font-medium group-hover:text-slate-900 transition-colors">Patrimoine Net</CardDescription>
          <div className="h-8 w-8 bg-slate-50 rounded-full flex items-center justify-center group-hover:bg-slate-200 transition-colors">
            <Activity className="h-4 w-4 text-slate-600" />
          </div>
        </CardHeader>
        <CardContent>
          <CardTitle className="text-2xl font-bold">
            <span className="amount-blur">{formatCurrency(analytics?.patrimoine_net_total || 0, "EUR")}</span>
          </CardTitle>
          <div className="flex items-center gap-2 mt-2">
            <Badge variant="outline" className="text-[10px] font-bold py-0 h-4 border-slate-200 text-slate-500">Global</Badge>
            <span className="text-[10px] text-slate-400">Tous les comptes</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
