import { useState, useEffect } from "react"
import { 
  TrendingUp, 
  Coins, 
  Percent, 
  Calendar,
  Info
} from "lucide-react"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts"
import { api } from "@/lib/api"
import { toast } from "sonner"

interface WealthSimulatorProps {
  initialCapitalDefault?: number
}

export function WealthSimulator({ initialCapitalDefault = 10000 }: WealthSimulatorProps) {
  const [params, setParams] = useState({
    initial_capital: initialCapitalDefault,
    monthly_contribution: 500,
    annual_return_pct: 7,
    years: 20
  })
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setParams(prev => ({ ...prev, initial_capital: initialCapitalDefault }))
  }, [initialCapitalDefault])

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const queryParams = new URLSearchParams({
          initial_capital: params.initial_capital.toString(),
          monthly_contribution: params.monthly_contribution.toString(),
          annual_return_pct: params.annual_return_pct.toString(),
          years: params.years.toString()
        })
        const res = await api.get(`/analytics/wealth-simulation?${queryParams.toString()}`)
        setData(res)
      } catch (error) {
        toast.error("Erreur lors de la simulation")
      } finally {
        setLoading(false)
      }
    }

    const timeoutId = setTimeout(fetchData, 300)
    return () => clearTimeout(timeoutId)
  }, [params])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("fr-FR", { 
      style: "currency", 
      currency: "EUR",
      maximumFractionDigits: 0
    }).format(value)
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border rounded-lg shadow-sm text-xs space-y-1.5">
          <p className="font-bold border-bottom pb-1 mb-1">Année {label}</p>
          <div className="flex justify-between gap-4">
            <span className="text-slate-500">Capital Initial:</span>
            <span className="font-medium">{formatCurrency(payload[0].value)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-500">Versements:</span>
            <span className="font-medium">{formatCurrency(payload[1].value)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-500">Intérêts:</span>
            <span className="font-medium text-emerald-600">{formatCurrency(payload[2].value)}</span>
          </div>
          <div className="pt-1 mt-1 border-t flex justify-between gap-4">
            <span className="font-bold">Total:</span>
            <span className="font-bold">{formatCurrency(payload[0].value + payload[1].value + payload[2].value)}</span>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          <CardTitle>Simulation de Patrimoine</CardTitle>
        </div>
        <CardDescription>
          Projetez la croissance de vos investissements sur le long terme.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="space-y-2">
            <Label htmlFor="initial_capital" className="flex items-center gap-1.5">
              <Coins className="h-3.5 w-3.5 text-muted-foreground" />
              Capital Initial
            </Label>
            <Input
              id="initial_capital"
              type="number"
              value={params.initial_capital}
              onChange={(e) => setParams({ ...params, initial_capital: Number(e.target.value) })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="monthly_contribution" className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
              Versement Mensuel
            </Label>
            <Input
              id="monthly_contribution"
              type="number"
              value={params.monthly_contribution}
              onChange={(e) => setParams({ ...params, monthly_contribution: Number(e.target.value) })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="annual_return_pct" className="flex items-center gap-1.5">
              <Percent className="h-3.5 w-3.5 text-muted-foreground" />
              Rendement Annuel (%)
            </Label>
            <Input
              id="annual_return_pct"
              type="number"
              step="0.5"
              value={params.annual_return_pct}
              onChange={(e) => setParams({ ...params, annual_return_pct: Number(e.target.value) })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="years" className="flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" />
              Durée (années)
            </Label>
            <Input
              id="years"
              type="number"
              value={params.years}
              onChange={(e) => setParams({ ...params, years: Number(e.target.value) })}
            />
          </div>
        </div>

        <div className="h-[350px] w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data?.items || []} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorInterest" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="year" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{ value: "Années", position: "insideBottom", offset: -5, fontSize: 10, fill: "#94a3b8" }}
              />
              <YAxis 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                tickFormatter={(val) => `${(val / 1000).toFixed(0)}k€`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36}/>
              <Area
                type="monotone"
                dataKey="initial_capital"
                name="Capital Initial"
                stackId="1"
                stroke="#cbd5e1"
                fill="#f1f5f9"
              />
              <Area
                type="monotone"
                dataKey="total_contributions"
                name="Versements"
                stackId="1"
                stroke="#94a3b8"
                fill="#e2e8f0"
              />
              <Area
                type="monotone"
                dataKey="total_interest"
                name="Intérêts"
                stackId="1"
                stroke="#10b981"
                fill="url(#colorInterest)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-100">
          <div className="flex flex-col">
            <span className="text-xs text-slate-500 uppercase font-semibold tracking-wider">Total Final</span>
            <span className="text-xl font-bold">{formatCurrency(data?.total_final || 0)}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-slate-500 uppercase font-semibold tracking-wider">Total Versements</span>
            <span className="text-xl font-semibold text-slate-600">{formatCurrency(data?.total_contributions || 0)}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-slate-500 uppercase font-semibold tracking-wider">Total Intérêts</span>
            <span className="text-xl font-semibold text-emerald-600">+{formatCurrency(data?.total_interest || 0)}</span>
          </div>
        </div>

        <div className="flex items-start gap-2 text-[11px] text-slate-400 bg-slate-50/50 p-2 rounded border border-dashed">
          <Info className="h-3 w-3 mt-0.5 shrink-0" />
          <p>
            Cette simulation utilise une composition mensuelle des intérêts. Les résultats sont donnés à titre indicatif et ne garantissent pas les performances futures.
            Le rendement affiché est brut d'inflation et de fiscalité.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
