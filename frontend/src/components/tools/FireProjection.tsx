import i18n from "i18next"
import { Trans, useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { Flame, Info } from "lucide-react"
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { keepSeriesOrder, numberFormatter } from "@/lib/chartTooltip"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorState } from "@/components/layout/ErrorState"
import { useIsMobile } from "@/hooks/useIsMobile"
import { formatCurrency, formatRate } from "@/lib/utils"
import { getAnalyticsFire } from "@/lib/api/analytics"

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
  if (years === null) return i18n.t("misc.overYears", { ns: "tools" })
  if (years === 0) return i18n.t("misc.alreadyReached", { ns: "tools" })
  const whole = Math.floor(years)
  const months = Math.round((years - whole) * 12)
  const monthsText = i18n.t("misc.months", { ns: "tools", count: months })
  const yearsText = i18n.t("misc.years", { ns: "tools", count: whole })
  if (whole === 0) return monthsText
  return months > 0 ? i18n.t("misc.yearsAndMonths", { ns: "tools", years: yearsText, months: monthsText }) : yearsText
}

const numberOrNull = (value: string) => (value.trim() !== "" && !Number.isNaN(Number(value)) ? value : null)

/** Indépendance financière (règle du taux de retrait) sur les dépenses et l'épargne réelles. */
export function FireProjection() {
  const { t } = useTranslation("tools")
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
        const res = await getAnalyticsFire<FireData>(`?${qs.toString()}`)
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
  if (error || !data) return <ErrorState message={t("fireProjection.impossibleDeCalculerLaProjection")} onRetry={() => setReload((n) => n + 1)} />

  return (
    <Card className="shadow-sm border-slate-100">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Flame className="h-5 w-5 text-amber-500" />
          <CardTitle className="text-lg">{t("fireProjection.independanceFinanciere")}</CardTitle>
        </div>
        <CardDescription>
          {t("misc.fireIntro", { rate: formatRate(data.withdrawal_rate_pct, 1) })}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-medium text-slate-500">{t("fireProjection.objectif")}</p>
            <p className="text-2xl font-black tabular-nums text-slate-900">{formatCurrency(data.target)}</p>
            <p className="text-xs text-slate-500">{t("misc.expensesPerYear", { amount: formatCurrency(data.annual_expenses) })}</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-medium text-slate-500">{t("fireProjection.atteintAujourdHui")}</p>
            <p className="text-2xl font-black tabular-nums text-slate-900"><span className="amount-blur">{formatRate(data.progress_pct, 1)}</span></p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-amber-500" style={{ width: `${data.progress_pct}%` }} />
            </div>
          </div>
          <div className="rounded-xl bg-amber-50 p-4">
            <p className="text-xs font-medium text-amber-700">{t("fireProjection.aCeRythme")}</p>
            <p className="text-2xl font-black text-slate-900">{formatYears(data.years_to_fi)}</p>
            {data.fi_year && data.years_to_fi !== 0 && <p className="text-xs text-amber-700">{t("misc.aroundYear", { year: data.fi_year })}</p>}
          </div>
        </div>

        {data.years_to_fi === null && (
          <div className="flex flex-col gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 sm:flex-row sm:items-center sm:justify-between">
            <span>
              {data.real_return_pct <= 0
                ? t("misc.negativeReal", { rate: formatRate(data.real_return_pct, 1) })
                : t("fireProjection.aCeRythmeDEpargne")}
            </span>
            {returnInput !== "5" && (
              <Button size="sm" variant="outline" className="h-10 shrink-0 bg-white md:h-9" onClick={() => setReturnInput("5")}>
                {t("fireProjection.essayerAvec5DeRendement")}
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
              <Tooltip itemSorter={keepSeriesOrder} formatter={numberFormatter((v: number) => formatCurrency(v))} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
              <Legend itemSorter={null} wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="wealth" name={t("fireProjection.patrimoineEurosDAujourdHui")} stroke="#f59e0b" fill="url(#fireWealth)" strokeWidth={3} />
              <Line type="monotone" dataKey="target" name={t("fireProjection.objectif")} stroke="#0f172a" strokeDasharray="5 4" dot={false} strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">{t("fireProjection.etSi")}</p>
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
              <Trans
                t={t}
                i18nKey="misc.fireNote"
                values={{
                  expenses: data.expenses_overridden ? t("misc.expensesEntered") : t("misc.expensesAvg", { count: data.months_used }),
                  savings: formatCurrency(data.monthly_savings),
                  savingsNote: data.savings_overridden ? t("misc.entered") : "",
                  nominal: formatRate(data.nominal_return_pct, 1),
                  inflation: formatRate(data.inflation_pct, 1),
                  real: formatRate(data.real_return_pct, 1),
                }}
                components={{ amount: <b className="amount-blur" />, real: <b /> }}
              />
            </span>
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 w-full text-sm font-medium text-slate-700 sm:w-auto">{t("fireProjection.tauxDeRetrait")}</span>
            {RATES.map((r) => (
              <Button key={r} size="sm" className="h-10 md:h-9" variant={rate === r ? "default" : "outline"} onClick={() => setRate(r)}>
                {formatRate(r, 1)}
              </Button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <label className="space-y-1 text-xs text-slate-500">
              {t("fireProjection.depensesAn")}
              <Input type="number" inputMode="decimal" className="h-10 md:h-9" placeholder={String(Math.round(data.annual_expenses))} value={expensesInput} onChange={(e) => setExpensesInput(e.target.value)} />
            </label>
            <label className="space-y-1 text-xs text-slate-500">
              {t("fireProjection.epargneMois")}
              <Input type="number" inputMode="decimal" className="h-10 md:h-9" placeholder={String(Math.round(data.monthly_savings))} value={savingsInput} onChange={(e) => setSavingsInput(e.target.value)} />
            </label>
            <label className="space-y-1 text-xs text-slate-500">
              {t("fireProjection.rendement")}
              <Input type="number" inputMode="decimal" className="h-10 md:h-9" placeholder={String(data.nominal_return_pct)} value={returnInput} onChange={(e) => setReturnInput(e.target.value)} />
            </label>
            <label className="space-y-1 text-xs text-slate-500">
              {t("fireProjection.inflation")}
              <Input type="number" inputMode="decimal" className="h-10 md:h-9" placeholder={String(data.inflation_pct)} value={inflationInput} onChange={(e) => setInflationInput(e.target.value)} />
            </label>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
