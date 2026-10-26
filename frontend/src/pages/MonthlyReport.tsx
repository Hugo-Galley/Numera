import { fetchCurrentBudgetMonth } from "@/lib/budgetPeriod"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { CheckCircle2, ChevronLeft, ChevronRight, ClipboardCheck, Printer } from "lucide-react"

import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Delta } from "@/components/monthly-report/Delta"
import { SpendingSection } from "@/components/monthly-report/SpendingSection"
import { BudgetSection } from "@/components/monthly-report/BudgetSection"
import { SavingsSection } from "@/components/monthly-report/SavingsSection"
import { WatchSection } from "@/components/monthly-report/WatchSection"
import type { BudgetLine, ClosureLite, MonthlyReportData } from "@/components/monthly-report/types"

const MONTHS = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]

function Headline({ label, value, children }: { label: string; value: string; children?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 sm:flex-col sm:items-stretch sm:justify-start sm:gap-0">
      <div className="min-w-0 sm:contents">
        <div className="text-xs font-medium text-slate-500">{label}</div>
        <div className="min-h-[1rem] sm:order-3">{children}</div>
      </div>
      <div className="amount-blur whitespace-nowrap text-xl font-black tabular-nums text-slate-900 sm:order-2 sm:text-2xl">{value}</div>
    </div>
  )
}

export default function IntelligentReport() {
  const [data, setData] = useState<MonthlyReportData | null>(null)
  const [budget, setBudget] = useState<BudgetLine[]>([])
  const [closure, setClosure] = useState<ClosureLite | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [date, setDate] = useState(() => {
    const d = new Date()
    return { month: d.getMonth() + 1, year: d.getFullYear() }
  })

  // Le premier chargement attend le mois budgétaire (sinon deux chargements : mois civil, puis mois de paie)
  const [ready, setReady] = useState(false)
  const [latest, setLatest] = useState<{ month: number; year: number } | null>(null)

  // Mois de paie : on ouvre le mois du dernier salaire reçu.
  useEffect(() => {
    fetchCurrentBudgetMonth()
      .then(current => {
        if (current) {
          setDate({ month: current.month, year: current.year })
          setLatest({ month: current.month, year: current.year })
        }
      })
      .finally(() => setReady(true))
  }, [])

  useEffect(() => {
    if (!ready) return
    let cancelled = false
    async function load() {
      setLoading(true)
      setFailed(false)
      const { month, year } = date
      const [report, alerts, closures] = await Promise.allSettled([
        api.get<MonthlyReportData>(`/analytics/monthly-report?month=${month}&year=${year}`),
        api.get<BudgetLine[]>(`/analytics/budget-alerts?month=${month}&year=${year}`),
        api.get<ClosureLite[]>("/month-review/closures"),
      ])
      if (cancelled) return
      if (report.status === "fulfilled") setData(report.value)
      else setFailed(true)
      setBudget(alerts.status === "fulfilled" ? alerts.value : [])
      setClosure(
        closures.status === "fulfilled"
          ? closures.value.find((c) => c.year === year && c.month === month) ?? null
          : null,
      )
      setLoading(false)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [date, ready])

  // Pas de rapport pour un mois à venir : on s'arrête au mois budgétaire en cours
  const now = new Date()
  const latestIndex = latest ? latest.year * 12 + latest.month : now.getFullYear() * 12 + now.getMonth() + 1
  const atLatest = date.year * 12 + date.month >= latestIndex

  const changeMonth = (delta: number) =>
    setDate(({ month, year }) => {
      const idx = year * 12 + (month - 1) + delta
      if (idx + 1 > latestIndex) return { month, year }
      return { month: (idx % 12) + 1, year: Math.floor(idx / 12) }
    })

  const hasExceptional = (data?.exceptional_expenses ?? 0) > 0
  const reviewLink = `/month/revue?year=${date.year}&month=${date.month}`

  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-12 md:space-y-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900">Bilan du mois</h1>
          <div className="mt-1">
            {closure ? (
              <Link to={reviewLink} className="inline-flex min-h-8 items-center gap-1.5 text-xs font-medium text-emerald-600 hover:underline md:min-h-0">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Mois clôturé
                {closure.unresolved_count > 0 && ` · ${closure.unresolved_count} point(s) non résolus`}
              </Link>
            ) : (
              <Link to={reviewLink} className="inline-flex min-h-8 items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 hover:underline md:min-h-0">
                <ClipboardCheck className="h-3.5 w-3.5" />
                Revue de fin de mois à faire
              </Link>
            )}
          </div>
        </div>
        <div className="no-print flex items-center gap-2">
          <div className="flex flex-1 items-center justify-between rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
            <Button variant="ghost" size="icon" className="h-11 w-11 md:h-9 md:w-9" onClick={() => changeMonth(-1)} aria-label="Mois précédent" disabled={loading}>
              <ChevronLeft className="h-5 w-5" />
            </Button>
            <span className="min-w-[150px] flex-1 text-center md:flex-none text-sm font-bold">
              {MONTHS[date.month - 1]} {date.year}
            </span>
            <Button variant="ghost" size="icon" className="h-11 w-11 md:h-9 md:w-9" onClick={() => changeMonth(1)} aria-label="Mois suivant" disabled={loading || atLatest}>
              <ChevronRight className="h-5 w-5" />
            </Button>
          </div>
          <Button variant="outline" size="icon" className="hidden h-11 w-11 md:inline-flex" onClick={() => window.print()} title="Exporter en PDF">
            <Printer className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {loading && !data ? (
        <div className="space-y-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : failed || !data ? (
        <Card>
          <CardContent className="space-y-3 p-8 text-center">
            <p className="text-slate-500">Impossible de charger le bilan.</p>
            <Button variant="outline" onClick={() => setDate({ ...date })}>Réessayer</Button>
          </CardContent>
        </Card>
      ) : (
        <div className={`space-y-8 transition-opacity ${loading ? "opacity-60" : ""}`}>
          <Card>
            <CardContent className="grid grid-cols-1 gap-4 divide-y divide-slate-100 p-5 sm:grid-cols-3 sm:gap-6 sm:divide-y-0 [&>div:not(:first-child)]:pt-4 sm:[&>div:not(:first-child)]:pt-0">
              <Headline label="Revenus" value={formatCurrency(data.income)}>
                <Delta diff={data.comparison.income_diff} pct={data.comparison.income_diff_pct} upIsBad={false} />
              </Headline>
              <Headline label="Dépenses réelles" value={formatCurrency(data.real_expenses)}>
                <Delta diff={data.comparison.expenses_diff} pct={data.comparison.expenses_diff_pct} />
                {hasExceptional && (
                  <div className="amount-blur text-[11px] text-slate-400">
                    {formatCurrency(data.real_expenses_excl_exceptional)} hors exceptionnel
                  </div>
                )}
              </Headline>
              <Headline
                label="Mis de côté"
                value={formatCurrency((data.money_flow?.savings.amount ?? 0) + (data.money_flow?.investments.amount ?? 0))}
              >
                <span className="text-xs text-slate-400">épargne + investi</span>
              </Headline>
            </CardContent>
          </Card>

          <SpendingSection data={data} month={date.month} year={date.year} />
          <BudgetSection lines={budget} />
          <SavingsSection data={data} />
          <WatchSection insights={data.insights} />
        </div>
      )}
    </div>
  )
}
