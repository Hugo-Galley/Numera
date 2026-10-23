import { useEffect, useState } from "react"
import { TrendingUp, Info } from "lucide-react"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

interface ForecastPoint {
  year: number
  base: number
  boosted: number
}

interface Forecast {
  current_wealth: number
  avg_monthly_savings: number
  months_used: number
  annual_return_pct: number
  years: number
  extra_monthly: number
  final_base: number
  final_boosted: number
  gain_from_extra: number
  points: ForecastPoint[]
}

const HORIZONS = [5, 10, 20]
const EXTRA_PRESETS = [0, 50, 100, 200]

export function WealthForecast() {
  const [years, setYears] = useState(10)
  const [extra, setExtra] = useState(0)
  const [data, setData] = useState<Forecast | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const res = await api.get<Forecast>(`/analytics/wealth-forecast?years=${years}&extra_monthly=${extra}`)
        if (!cancelled) {
          setData(res)
          setError(false)
        }
      } catch {
        if (!cancelled) setError(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [years, extra])

  if (loading && !data) return <Skeleton className="h-[480px] w-full rounded-xl" />
  if (error || !data) {
    return <p className="text-sm text-rose-600">Impossible de calculer la prévision.</p>
  }

  const boostedShown = data.extra_monthly !== 0
  const final = boostedShown ? data.final_boosted : data.final_base

  return (
    <div className="space-y-6">
      <Card className="shadow-sm border-slate-100">
        <CardHeader>
          <CardDescription>Dans {data.years} ans, tu auras environ</CardDescription>
          <CardTitle className="text-4xl sm:text-5xl font-black tracking-tight tabular-nums text-slate-900 amount-blur">
            {formatCurrency(final, "EUR")}
          </CardTitle>
          {boostedShown && (
            <p className="text-sm font-bold text-emerald-600 amount-blur">
              {data.gain_from_extra >= 0 ? "+" : ""}
              {formatCurrency(data.gain_from_extra, "EUR")} grâce à {data.extra_monthly > 0 ? "+" : ""}
              {data.extra_monthly} €/mois
            </p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-500 flex items-start gap-2">
            <Info className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              Tu pars de <b className="amount-blur">{formatCurrency(data.current_wealth, "EUR")}</b>, tu épargnes en
              moyenne <b className="amount-blur">{formatCurrency(data.avg_monthly_savings, "EUR")}</b> par mois
              {data.months_used > 0 ? ` (sur ${data.months_used} derniers mois)` : ""}, avec un rendement d'environ{" "}
              <b>{data.annual_return_pct.toFixed(1)} %</b> par an selon la répartition de ton patrimoine.
            </span>
          </p>
          {data.avg_monthly_savings < 0 && (
            <p className="text-sm font-medium text-amber-600">
              Tu dépenses plus que tu ne gagnes en moyenne : le patrimoine diminue dans cette prévision.
            </p>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 w-full text-sm font-medium text-slate-700 sm:w-auto">J'épargne en plus :</span>
            {EXTRA_PRESETS.map((v) => (
              <Button
                key={v}
                size="sm"
                className="h-10 md:h-9"
                variant={extra === v ? "default" : "outline"}
                onClick={() => setExtra(v)}
              >
                {v === 0 ? "Rien" : `+${v} €`}
              </Button>
            ))}
            <Input
              type="number"
              className="h-10 w-28 md:h-9"
              placeholder="Autre"
              value={EXTRA_PRESETS.includes(extra) ? "" : extra}
              onChange={(e) => setExtra(Number(e.target.value) || 0)}
            />
            <span className="text-sm text-slate-500">€/mois</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 w-full text-sm font-medium text-slate-700 sm:w-auto">Horizon :</span>
            {HORIZONS.map((h) => (
              <Button key={h} size="sm" className="h-10 flex-1 sm:flex-none md:h-9" variant={years === h ? "default" : "outline"} onClick={() => setYears(h)}>
                {h} ans
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-blue-500" /> Évolution prévue
          </CardTitle>
        </CardHeader>
        <CardContent className="h-[260px] px-2 md:h-[360px] md:px-6">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.points} margin={{ top: 10, right: 12, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="year" tickFormatter={(v) => `${v} an${v > 1 ? "s" : ""}`} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" minTickGap={16} />
              <YAxis
                tick={{ fontSize: 12, fill: "#64748b" }}
                tickFormatter={(v) => `${Math.round(v / 1000)}k€`}
                width={52}
              />
              <Tooltip
                contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
                labelFormatter={(v) => `Dans ${v} an${Number(v) > 1 ? "s" : ""}`}
                formatter={(v: number) => formatCurrency(v, "EUR")}
              />
              <Legend />
              <Line type="monotone" dataKey="base" name="Au rythme actuel" stroke="#3b82f6" strokeWidth={3} dot={false} />
              {boostedShown && (
                <Line type="monotone" dataKey="boosted" name={`Avec ${data.extra_monthly > 0 ? "+" : ""}${data.extra_monthly} €/mois`} stroke="#10b981" strokeWidth={3} dot={false} />
              )}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
