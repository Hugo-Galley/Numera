import { History as HistoryIcon, Activity, Layers } from "lucide-react"
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
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line
} from "recharts"

const months = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

interface HistoryTabProps {
  kpiHistory: any[]
  burnRateSeries: any[]
  salarySeries: any[]
  displayCurrency: string
}

export function HistoryTab({
  kpiHistory,
  burnRateSeries,
  salarySeries,
  displayCurrency
}: HistoryTabProps) {
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <div className="flex items-center gap-2">
            <HistoryIcon className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Flux de trésorerie</CardTitle>
          </div>
          <CardDescription>Revenus vs Dépenses (6 mois).</CardDescription>
        </CardHeader>
        <CardContent className="p-0 sm:p-6 h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={kpiHistory} margin={{ top: 40, right: 30, left: 20, bottom: 20 }}>
              <defs>
                <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/><stop offset="95%" stopColor="#10b981" stopOpacity={0}/></linearGradient>
                <linearGradient id="colorDep" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f43f5e" stopOpacity={0.1}/><stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(v) => `${v}${displayCurrency === 'EUR' ? '€' : displayCurrency}`} />
              <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
              <Legend verticalAlign="top" height={36}/>
              <Area type="monotone" dataKey="revenus" name="Revenus" stroke="#10b981" fill="url(#colorRev)" strokeWidth={3} />
              <Area type="monotone" dataKey="depenses" name="Dépenses" stroke="#f43f5e" fill="url(#colorDep)" strokeWidth={3} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Évolution du Burn Rate</CardTitle>
          </div>
          <CardDescription>Dépense moyenne journalière par mois.</CardDescription>
        </CardHeader>
        <CardContent className="p-0 sm:p-6 h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={burnRateSeries} margin={{ top: 40, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="month" 
                axisLine={false} 
                tickLine={false} 
                tickFormatter={(v) => months[v-1]?.substring(0, 3) || v} 
                tick={{ fontSize: 12, fill: '#64748b' }} 
              />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(v) => `${v}${displayCurrency === 'EUR' ? '€' : displayCurrency}`} />
              <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => `${v.toFixed(2)}${displayCurrency === 'EUR' ? '€' : displayCurrency} / jour`} />
              <Line type="monotone" dataKey="burn_rate" name="Burn Rate" stroke="#0f172a" strokeWidth={4} dot={{ r: 4, fill: "#0f172a" }} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Évolution du Salaire</CardTitle>
          </div>
          <CardDescription>Stabilité et croissance des revenus principaux.</CardDescription>
        </CardHeader>
        <CardContent className="p-0 sm:p-6 h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={salarySeries} margin={{ top: 40, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="month" 
                axisLine={false} 
                tickLine={false} 
                tickFormatter={(v) => months[v-1]?.substring(0, 3) || v} 
                tick={{ fontSize: 12, fill: '#64748b' }} 
              />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(v) => `${v}${displayCurrency === 'EUR' ? '€' : displayCurrency}`} />
              <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
              <Line type="stepAfter" dataKey="salary" name="Salaire" stroke="#0f172a" strokeWidth={4} dot={{ r: 4, fill: "#0f172a" }} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
