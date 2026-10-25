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

interface SavingsMonth {
  label: string
  revenus: number
  depenses_reelles: number
  epargne_flow: number
}

interface ReturnItem {
  type: string
  balance: number
  rate_pct: number
  source: "observed" | "manual" | "none"
}

const TYPE_LABELS: Record<string, string> = {
  investissement: "Comptes d'investissement",
  autres: "Courant et épargne",
}

interface Forecast {
  computed_monthly_savings: number
  observed_investment_return_pct: number | null
  savings_overridden: boolean
  savings_months: SavingsMonth[]
  return_breakdown: ReturnItem[]
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
  const [savingsInput, setSavingsInput] = useState("")
  const [investInput, setInvestInput] = useState("")
  const [otherInput, setOtherInput] = useState("")
  const [data, setData] = useState<Forecast | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const qs = new URLSearchParams({ years: String(years), extra_monthly: String(extra) })
        if (savingsInput.trim() !== "" && !Number.isNaN(Number(savingsInput))) qs.set("monthly_savings", savingsInput)
        if (investInput.trim() !== "" && !Number.isNaN(Number(investInput))) qs.set("investment_return_pct", investInput)
        if (otherInput.trim() !== "" && !Number.isNaN(Number(otherInput))) qs.set("savings_return_pct", otherInput)
        const res = await api.get<Forecast>(`/analytics/wealth-forecast?${qs.toString()}`)
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
  }, [years, extra, savingsInput, investInput, otherInput])

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
              {data.savings_overridden
                ? " (valeur saisie)"
                : data.months_used > 0
                  ? ` (revenus − dépenses, moyenne sur ${data.months_used} mois)`
                  : ""}
              , avec un rendement de <b>{data.annual_return_pct.toFixed(1)} %</b> par an
              {data.return_breakdown.some((r) => r.source === "manual") ? " (en partie saisi)" : " (rendement constaté sur tes investissements)"}. Détail plus bas.
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
              type="number" inputMode="decimal"
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
          <CardTitle className="text-lg">Comment c'est calculé</CardTitle>
          <CardDescription>
            Chaque mois : patrimoine × (1 + rendement mensuel) + épargne mensuelle, répété sur {data.years} ans. Modifie
            les deux hypothèses ci-dessous pour les remplacer.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-slate-700">Épargne mensuelle :</span>
              <Input
                type="number" inputMode="decimal"
                className="h-10 w-28 md:h-9"
                placeholder={String(Math.round(data.computed_monthly_savings))}
                value={savingsInput}
                onChange={(e) => setSavingsInput(e.target.value)}
              />
              <span className="text-sm text-slate-500">€/mois</span>
              {data.savings_overridden && (
                <Button size="sm" variant="ghost" onClick={() => setSavingsInput("")}>
                  Revenir au calcul ({formatCurrency(data.computed_monthly_savings, "EUR")})
                </Button>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Calcul automatique = revenus − dépenses réelles (hors versements vers l'épargne et les investissements),
              moyenne sur {data.months_used} mois. Ce n'est pas la somme que tu verses sur tes comptes : c'est ce qu'il
              te reste en fin de mois.
            </p>
            {data.savings_months.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-xs tabular-nums">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="py-1 pr-3 font-medium">Mois</th>
                      <th className="py-1 pr-3 text-right font-medium">Revenus</th>
                      <th className="py-1 pr-3 text-right font-medium">Dépenses réelles</th>
                      <th className="py-1 text-right font-medium">Reste</th>
                    </tr>
                  </thead>
                  <tbody className="amount-blur">
                    {data.savings_months.map((m) => (
                      <tr key={m.label} className="border-t border-slate-100">
                        <td className="py-1 pr-3">{m.label}</td>
                        <td className="py-1 pr-3 text-right">{formatCurrency(m.revenus, "EUR")}</td>
                        <td className="py-1 pr-3 text-right">{formatCurrency(m.depenses_reelles, "EUR")}</td>
                        <td className="py-1 text-right font-semibold">{formatCurrency(m.epargne_flow, "EUR")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-700">Rendement annuel</p>
            {data.return_breakdown.map((r) => {
              const isInvest = r.type === "investissement"
              const value = isInvest ? investInput : otherInput
              const setValue = isInvest ? setInvestInput : setOtherInput
              return (
                <div key={r.type} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="w-44 text-slate-700">{TYPE_LABELS[r.type] ?? r.type}</span>
                  <span className="w-24 text-xs tabular-nums text-slate-500 amount-blur">
                    {formatCurrency(r.balance, "EUR")}
                  </span>
                  <Input
                    type="number" inputMode="decimal"
                    className="h-10 w-24 md:h-9"
                    placeholder={r.rate_pct.toFixed(1)}
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                  />
                  <span className="text-slate-500">%</span>
                  {r.source === "manual" ? (
                    <Button size="sm" variant="ghost" onClick={() => setValue("")}>
                      Revenir à {isInvest && data.observed_investment_return_pct !== null ? `${data.observed_investment_return_pct.toFixed(1)} % constaté` : "0 %"}
                    </Button>
                  ) : (
                    <span className="text-xs text-slate-400">{r.source === "observed" ? "constaté" : "aucune donnée, 0 %"}</span>
                  )}
                </div>
              )
            })}
            <p className="text-xs text-slate-500">
              Investissement : rendement annualisé (XIRR) réellement constaté sur tes comptes titres valorisés par
              positions, appliqué à tous tes comptes d'investissement. Courant et épargne : 0 % tant que tu n'en saisis
              pas un. Moyenne pondérée par les soldes : {data.annual_return_pct.toFixed(1)} %.
            </p>
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
