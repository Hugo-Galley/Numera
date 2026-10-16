import { useCallback, useEffect, useState, type ReactNode } from "react"
import { useSearchParams } from "react-router-dom"
import { Gift, Play, Receipt, Store, TrendingUp, Repeat, CalendarRange } from "lucide-react"
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { WrappedStory } from "@/components/wrapped/WrappedStory"
import { Delta, hoursLabel, monthName, monthShort } from "@/components/wrapped/format"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import { useWorkTime } from "@/providers/WorkTimeProvider"
import type { WrappedReport } from "@/types/wrapped"

function Kpi({ label, value, delta }: { label: string; value: string; delta?: ReactNode }) {
  return (
    <Card className="shadow-sm">
      <CardContent className="space-y-1 p-5">
        <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</p>
        <p className="text-2xl font-black tracking-tight amount-blur">{value}</p>
        <div className="min-h-5">{delta}</div>
      </CardContent>
    </Card>
  )
}

function Section({ icon, title, description, children }: { icon: ReactNode; title: string; description?: string; children: ReactNode }) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          {icon}
          {title}
        </CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

export default function Wrapped() {
  const [params, setParams] = useSearchParams()
  const year = Number(params.get("year")) || new Date().getFullYear()
  const [report, setReport] = useState<WrappedReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [storyOpen, setStoryOpen] = useState(false)
  const { workTime } = useWorkTime()
  const hoursPerDay = workTime?.work_hours_per_day ?? 7

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setReport(await api.get<WrappedReport>(`/analytics/wrapped?year=${year}`))
    } catch (error) {
      console.error("Erreur lors du chargement du bilan annuel", error)
      setReport(null)
    } finally {
      setLoading(false)
    }
  }, [year])

  useEffect(() => {
    load()
  }, [load])

  const years = report?.available_years.length ? report.available_years : [year]
  const prev = report?.previous ?? null
  const period = report?.is_partial ? `Janvier → ${monthName(report.months_covered)}` : "Année complète"

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight">Bilan annuel</h1>
          <p className="text-muted-foreground">Ton année en chiffres, comparée à la précédente.</p>
        </div>
        <Select value={String(year)} onValueChange={(v) => setParams({ year: v })}>
          <SelectTrigger className="w-full sm:w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {years.map((y) => (
              <SelectItem key={y} value={String(y)}>
                {y}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="space-y-6">
          <Skeleton className="h-44 w-full rounded-2xl" />
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28" />
            ))}
          </div>
          <Skeleton className="h-72 w-full" />
        </div>
      ) : !report || !report.has_data ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Gift className="h-10 w-10 text-slate-300" />
            <p className="font-semibold">Aucune donnée pour {year}</p>
            <p className="text-sm text-muted-foreground">Importe ou saisis des transactions pour générer ce bilan.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 p-6 text-white shadow-md sm:p-8">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-white/60">{period}</p>
                <p className="text-6xl font-black tracking-tight">{report.year}</p>
                <p className="text-white/70">
                  {report.totals.expense_count.toLocaleString("fr-FR")} dépenses, {report.top_merchants.length ? `${report.top_merchants[0].merchant} en tête` : "aucun marchand"}.
                </p>
              </div>
              <Button size="lg" onClick={() => setStoryOpen(true)} className="bg-white text-slate-950 hover:bg-white/90">
                <Play className="mr-2 h-4 w-4" /> Revivre mon année
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi
              label="Revenus"
              value={formatCurrency(report.totals.income)}
              delta={prev && <Delta value={prev.income_change_pct} vsYear={prev.year} />}
            />
            <Kpi
              label="Dépenses réelles"
              value={formatCurrency(report.totals.real_expenses)}
              delta={prev && <Delta value={prev.real_expenses_change_pct} higherIsBetter={false} vsYear={prev.year} />}
            />
            <Kpi
              label="Taux d'épargne"
              value={`${report.totals.savings_rate.toLocaleString("fr-FR")} %`}
              delta={prev && <Delta value={prev.savings_rate_change_pts} unit="pts" vsYear={prev.year} />}
            />
            <Kpi
              label="Patrimoine"
              value={`${report.totals.net_worth_change >= 0 ? "+" : ""}${formatCurrency(report.totals.net_worth_change)}`}
              delta={
                report.net_worth_change_pct !== null && (
                  <span className="text-sm text-muted-foreground">
                    {report.net_worth_change_pct > 0 ? "+" : ""}
                    {report.net_worth_change_pct.toLocaleString("fr-FR")} % sur l'année
                  </span>
                )
              }
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Section icon={<CalendarRange className="h-5 w-5 text-slate-400" />} title="Mois par mois">
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={report.months} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="month" tickFormatter={monthShort} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#64748b" }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} width={36} />
                      <Tooltip
                        labelFormatter={(m: number) => monthName(m)}
                        formatter={(v: number) => formatCurrency(v)}
                        contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
                      />
                      <Legend />
                      <Bar dataKey="income" name="Revenus" fill="#10b981" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="real_expenses" name="Dépenses" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                  {report.most_expensive_month && (
                    <p>
                      <span className="text-muted-foreground">Mois le plus cher : </span>
                      <span className="font-semibold capitalize">{monthName(report.most_expensive_month.month)}</span>{" "}
                      <span className="amount-blur">({formatCurrency(report.most_expensive_month.real_expenses)})</span>
                    </p>
                  )}
                  {report.thriftiest_month && (
                    <p>
                      <span className="text-muted-foreground">Mois le plus sobre : </span>
                      <span className="font-semibold capitalize">{monthName(report.thriftiest_month.month)}</span>{" "}
                      <span className="amount-blur">({formatCurrency(report.thriftiest_month.real_expenses)})</span>
                    </p>
                  )}
                </div>
              </Section>
            </div>

            <Section icon={<Receipt className="h-5 w-5 text-slate-400" />} title="Plus gros postes">
              <ol className="space-y-3">
                {report.top_categories.map((c) => (
                  <li key={c.name} className="space-y-1">
                    <div className="flex justify-between gap-3 text-sm">
                      <span className="font-medium">{c.name}</span>
                      <span className="font-bold amount-blur">{formatCurrency(c.total)}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-100">
                      <div className="h-1.5 rounded-full" style={{ width: `${c.percentage}%`, backgroundColor: c.color || "#0f172a" }} />
                    </div>
                    {hoursLabel(c.work_hours, hoursPerDay) && (
                      <p className="text-[11px] text-muted-foreground amount-blur">{hoursLabel(c.work_hours, hoursPerDay)}</p>
                    )}
                  </li>
                ))}
              </ol>
            </Section>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Section icon={<Store className="h-5 w-5 text-slate-400" />} title="Top marchands">
              <ol className="space-y-2">
                {report.top_merchants.map((m, i) => (
                  <li key={m.merchant} className="flex items-center justify-between gap-3 text-sm">
                    <span className="truncate">
                      <span className="mr-2 font-bold text-muted-foreground">{i + 1}</span>
                      {m.merchant}
                    </span>
                    <span className="shrink-0 font-bold amount-blur">{formatCurrency(m.total)}</span>
                  </li>
                ))}
              </ol>
              {report.biggest_expense && (
                <div className="mt-5 rounded-xl border bg-slate-50/60 p-4 text-sm">
                  <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Plus grosse dépense</p>
                  <p className="mt-1">
                    <span className="font-black amount-blur">{formatCurrency(report.biggest_expense.amount)}</span> · {report.biggest_expense.merchant}
                    <span className="text-muted-foreground">
                      {" "}
                      le {new Date(report.biggest_expense.date).toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}
                    </span>
                  </p>
                  {hoursLabel(report.biggest_expense.work_hours, hoursPerDay) && (
                    <p className="text-xs text-muted-foreground amount-blur">{hoursLabel(report.biggest_expense.work_hours, hoursPerDay)}</p>
                  )}
                </div>
              )}
            </Section>

            <div className="space-y-6">
              <Section icon={<TrendingUp className="h-5 w-5 text-slate-400" />} title="Patrimoine & investissements">
                <dl className="grid grid-cols-2 gap-4 text-sm">
                  {[
                    ["Début d'année", formatCurrency(report.totals.net_worth_start)],
                    [report.is_partial ? "Aujourd'hui" : "Fin d'année", formatCurrency(report.totals.net_worth_end)],
                    ["Investi / épargné", formatCurrency(report.totals.invested)],
                    ["Dividendes", formatCurrency(report.totals.dividends)],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt className="text-muted-foreground">{label}</dt>
                      <dd className="text-lg font-black amount-blur">{value}</dd>
                    </div>
                  ))}
                </dl>
                {prev && <Delta value={prev.invested_change_pct} vsYear={prev.year} className="mt-2" />}
              </Section>

              <Section
                icon={<Repeat className="h-5 w-5 text-slate-400" />}
                title="Abonnements"
                description={`${formatCurrency(report.totals.subscriptions_cost)} payés sur la période`}
              >
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Nouveaux</p>
                    {report.new_subscriptions.length ? (
                      <ul className="mt-1 space-y-0.5">
                        {report.new_subscriptions.map((s) => (
                          <li key={s.name}>{s.name}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-1 text-muted-foreground">Aucun</p>
                    )}
                  </div>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Arrêtés</p>
                    {report.stopped_subscriptions.length ? (
                      <>
                        <ul className="mt-1 space-y-0.5">
                          {report.stopped_subscriptions.map((s) => (
                            <li key={s.name}>{s.name}</li>
                          ))}
                        </ul>
                        <p className="mt-1 font-semibold text-emerald-600 amount-blur">
                          {formatCurrency(report.stopped_subscriptions_yearly_saving)} / an économisés
                        </p>
                      </>
                    ) : (
                      <p className="mt-1 text-muted-foreground">Aucun</p>
                    )}
                  </div>
                </div>
              </Section>
            </div>
          </div>

          {storyOpen && <WrappedStory report={report} onClose={() => setStoryOpen(false)} />}
        </>
      )}
    </div>
  )
}
