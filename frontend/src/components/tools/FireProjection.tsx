import { useEffect, useState } from "react"
import { Flame, Info } from "lucide-react"
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorState } from "@/components/layout/ErrorState"
import { useIsMobile } from "@/hooks/useIsMobile"
import { api } from "@/lib/api"
import { formatCurrency, formatRate } from "@/lib/utils"

interface FireScenario {
  label: string
  monthly_savings: number
  annual_expenses: number
  years_to_fi: number | null
}

interface FireData {
  current_wealth: number
  annual_expenses: number
  expenses_overridden: boolean
  withdrawal_rate_pct: number
  target: number
  progress_pct: number
  monthly_savings: number
  savings_overridden: boolean
  nominal_return_pct: number
  inflation_pct: number
  real_return_pct: number
  months_used: number
  years_to_fi: number | null
  fi_year: number | null
  points: { year: number; wealth: number; target: number }[]
  scenarios: FireScenario[]
}

const RATES = [3, 3.5, 4]

const formatYears = (years: number | null) => {
  if (years === null) return "plus de 80 ans"
  if (years === 0) return "déjà atteinte"
  const whole = Math.floor(years)
  const months = Math.round((years - whole) * 12)
  if (whole === 0) return `${months} mois`
  return months > 0 ? `${whole} ans et ${months} mois` : `${whole} ans`
}

const numberOrNull = (value: string) => (value.trim() !== "" && !Number.isNaN(Number(value)) ? value : null)

/** Indépendance financière (règle du taux de retrait) sur les dépenses et l'épargne réelles. */
export function FireProjection() {
  const isMobile = useIsMobile()
  const [rate, setRate] = useState(4)
  const [expensesInput, setExpensesInput] = useState("")
  const [savingsInput, setSavingsInput] = useState("")
  const [returnInput, setReturnInput] = useState("")
  const [inflationInput, setInflationInput] = useState("")
  const [data, setData] = useState<FireData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const qs = new URLSearchParams({ withdrawal_rate_pct: String(rate) })
        const overrides: [string, string][] = [
          ["annual_expenses", expensesInput],
          ["monthly_savings", savingsInput],
          ["return_pct", returnInput],
          ["inflation_pct", inflationInput],
        ]
        overrides.forEach(([key, value]) => {
          const v = numberOrNull(value)
          if (v !== null) qs.set(key, v)
        })
        const res = await api.get<FireData>(`/analytics/fire?${qs.toString()}`)
        if (!cancelled) {
          setData(res)
          setError(false)
        }
      } catch {
        if (!cancelled) setError(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 250)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [rate, expensesInput, savingsInput, returnInput, inflationInput, reload])

  if (loading && !data) return <Skeleton className="h-[420px] w-full rounded-xl" />
  if (error || !data) return <ErrorState message="Impossible de calculer la projection d'indépendance financière." onRetry={() => setReload((n) => n + 1)} />

  return (
    <Card className="shadow-sm border-slate-100">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Flame className="h-5 w-5 text-amber-500" />
          <CardTitle className="text-lg">Indépendance financière</CardTitle>
        </div>
        <CardDescription>
          Le jour où ton patrimoine couvre tes dépenses : {formatRate(data.withdrawal_rate_pct, 1)} retirés chaque année suffisent à vivre.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-medium text-slate-500">Objectif</p>
            <p className="text-2xl font-black tabular-nums text-slate-900">{formatCurrency(data.target)}</p>
            <p className="text-xs text-slate-500">{formatCurrency(data.annual_expenses)} de dépenses par an</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-medium text-slate-500">Atteint aujourd'hui</p>
            <p className="text-2xl font-black tabular-nums text-slate-900"><span className="amount-blur">{formatRate(data.progress_pct, 1)}</span></p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-amber-500" style={{ width: `${data.progress_pct}%` }} />
            </div>
          </div>
          <div className="rounded-xl bg-amber-50 p-4">
            <p className="text-xs font-medium text-amber-700">À ce rythme</p>
            <p className="text-2xl font-black text-slate-900">{formatYears(data.years_to_fi)}</p>
            {data.fi_year && data.years_to_fi !== 0 && <p className="text-xs text-amber-700">vers {data.fi_year}</p>}
          </div>
        </div>

        {data.years_to_fi === null && (
          <div className="flex flex-col gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 sm:flex-row sm:items-center sm:justify-between">
            <span>
              {data.real_return_pct <= 0
                ? `Avec un rendement réel de ${formatRate(data.real_return_pct, 1)} (patrimoine surtout en liquidités), l'inflation ronge l'épargne : l'objectif n'est pas atteignable.`
                : "À ce rythme d'épargne, l'objectif n'est pas atteint avant 80 ans."}
            </span>
            {returnInput !== "5" && (
              <Button size="sm" variant="outline" className="h-10 shrink-0 bg-white md:h-9" onClick={() => setReturnInput("5")}>
                Essayer avec 5 % de rendement
              </Button>
            )}
          </div>
        )}

        <div className="h-[240px] md:h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data.points} margin={isMobile ? { top: 8, right: 8, left: 0, bottom: 0 } : { top: 10, right: 20, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="fireWealth" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} />
              <YAxis width={isMobile ? 48 : 70} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v) => `${Math.round(v / 1000)} k€`} />
              <Tooltip formatter={(v: number) => formatCurrency(v)} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="wealth" name="Patrimoine (euros d'aujourd'hui)" stroke="#f59e0b" fill="url(#fireWealth)" strokeWidth={3} />
              <Line type="monotone" dataKey="target" name="Objectif" stroke="#0f172a" strokeDasharray="5 4" dot={false} strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">Et si…</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            {data.scenarios.map((s) => (
              <div key={s.label} className={`rounded-xl border p-3 ${s.label === "Actuel" ? "border-amber-300 bg-amber-50/50" : ""}`}>
                <p className="text-xs font-medium text-slate-500">{s.label}</p>
                <p className="text-sm font-bold text-slate-900">{formatYears(s.years_to_fi)}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3 border-t pt-4">
          <p className="flex items-start gap-2 text-sm text-slate-500">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Dépenses {data.expenses_overridden ? "saisies" : `réelles moyennes sur ${data.months_used} mois`}, épargne de{" "}
              <b className="amount-blur">{formatCurrency(data.monthly_savings)}</b> par mois{data.savings_overridden ? " (saisie)" : ""}, rendement{" "}
              {formatRate(data.nominal_return_pct, 1)} moins {formatRate(data.inflation_pct, 1)} d'inflation, soit{" "}
              <b>{formatRate(data.real_return_pct, 1)}</b> réel. Tout est exprimé en euros d'aujourd'hui.
            </span>
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 w-full text-sm font-medium text-slate-700 sm:w-auto">Taux de retrait :</span>
            {RATES.map((r) => (
              <Button key={r} size="sm" className="h-10 md:h-9" variant={rate === r ? "default" : "outline"} onClick={() => setRate(r)}>
                {formatRate(r, 1)}
              </Button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <label className="space-y-1 text-xs text-slate-500">
              Dépenses / an (€)
              <Input type="number" inputMode="decimal" className="h-10 md:h-9" placeholder={String(Math.round(data.annual_expenses))} value={expensesInput} onChange={(e) => setExpensesInput(e.target.value)} />
            </label>
            <label className="space-y-1 text-xs text-slate-500">
              Épargne / mois (€)
              <Input type="number" inputMode="decimal" className="h-10 md:h-9" placeholder={String(Math.round(data.monthly_savings))} value={savingsInput} onChange={(e) => setSavingsInput(e.target.value)} />
            </label>
            <label className="space-y-1 text-xs text-slate-500">
              Rendement (%)
              <Input type="number" inputMode="decimal" className="h-10 md:h-9" placeholder={String(data.nominal_return_pct)} value={returnInput} onChange={(e) => setReturnInput(e.target.value)} />
            </label>
            <label className="space-y-1 text-xs text-slate-500">
              Inflation (%)
              <Input type="number" inputMode="decimal" className="h-10 md:h-9" placeholder={String(data.inflation_pct)} value={inflationInput} onChange={(e) => setInflationInput(e.target.value)} />
            </label>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
