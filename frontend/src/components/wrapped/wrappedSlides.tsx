import i18n from "i18next"
import { Trans } from "react-i18next"
import { appLocale, percentSuffix } from "@/i18n/locale"
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from "recharts"
import { Delta, hoursLabel, monthName, monthShort } from "./format"
import { type ReactNode } from "react"
import { type WrappedReport } from "@/types/wrapped"
import { cn, formatCurrency } from "@/lib/utils"

export interface Slide {
  key: string
  /** Dégradé de fond de la carte */
  tone: string
  content: ReactNode
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-xs font-bold uppercase tracking-[0.2em] text-white/60 sm:text-sm">{children}</p>
}

export function Big({ children, className, blur = true }: { children: ReactNode; className?: string; blur?: boolean }) {
  return <p className={cn("break-words text-4xl font-black tracking-tight text-white min-[400px]:text-5xl sm:text-7xl", blur && "amount-blur", className)}>{children}</p>
}

export function Sub({ children }: { children: ReactNode }) {
  return <p className="text-base text-white/80 min-[400px]:text-lg sm:text-xl">{children}</p>
}

export function buildSlides(report: WrappedReport, hoursPerDay: number): Slide[] {
  const t = i18n.getFixedT(null, "wrapped")
  const { totals, previous: prev, year } = report
  const period = report.is_partial ? t("wrappedSlides.periodPartial", { month: monthName(report.months_covered) }) : t("wrappedSlides.periodFull")
  const slides: Slide[] = []

  slides.push({
    key: "intro",
    tone: "from-slate-950 via-indigo-950 to-slate-900",
    content: (
      <>
        <Eyebrow>{t("wrappedSlides.tonBilan")}</Eyebrow>
        <Big className="sm:text-8xl" blur={false}>{year}</Big>
        <Sub>
          {t("wrappedSlides.introSub", { period, count: totals.expense_count.toLocaleString(appLocale()) })}
        </Sub>
      </>
    ),
  })

  slides.push({
    key: "flows",
    tone: "from-emerald-950 via-slate-950 to-slate-900",
    content: (
      <>
        <Eyebrow>{t("wrappedSlides.ceQuiEstEntre")}</Eyebrow>
        <Big>{formatCurrency(totals.income)}</Big>
        {prev && <Delta value={prev.income_change_pct} vsYear={prev.year} />}
        <div className="mt-6 space-y-2">
          <Eyebrow>{t("wrappedSlides.ceQuiEstSorti")}</Eyebrow>
          <p className="text-3xl font-black text-white min-[400px]:text-4xl sm:text-5xl amount-blur">{formatCurrency(totals.real_expenses)}</p>
          {prev && <Delta value={prev.real_expenses_change_pct} higherIsBetter={false} vsYear={prev.year} />}
          {hoursLabel(report.real_expenses_work_hours, hoursPerDay) && (
            <p className="text-white/60 amount-blur">{hoursLabel(report.real_expenses_work_hours, hoursPerDay)}</p>
          )}
        </div>
      </>
    ),
  })

  slides.push({
    key: "savings",
    tone: totals.saved >= 0 ? "from-teal-900 via-emerald-950 to-slate-950" : "from-rose-950 via-slate-950 to-slate-900",
    content: (
      <>
        <Eyebrow>{t("wrappedSlides.tuAsMisDeCote")}</Eyebrow>
        <Big className="sm:text-8xl">{totals.savings_rate.toLocaleString(appLocale())}{percentSuffix()}</Big>
        <Sub>
          {t("wrappedSlides.deTesRevenusSoit")} <span className="font-bold text-white amount-blur">{formatCurrency(totals.saved)}</span>.
        </Sub>
        {prev && <Delta value={prev.savings_rate_change_pts} unit="pts" vsYear={prev.year} />}
      </>
    ),
  })

  const topCat = report.top_categories[0]
  if (topCat) {
    slides.push({
      key: "category",
      tone: "from-amber-900 via-slate-950 to-slate-950",
      content: (
        <>
          <Eyebrow>{t("wrappedSlides.tonPlusGrosPoste")}</Eyebrow>
          <Big blur={false}>{topCat.name}</Big>
          <Sub>
            <span className="font-bold text-white amount-blur">{formatCurrency(topCat.total)}</span>{t("wrappedSlides.topCatShare", { pct: topCat.percentage.toLocaleString(appLocale()) })}
          </Sub>
          {hoursLabel(topCat.work_hours, hoursPerDay) && <p className="text-white/60 amount-blur">{hoursLabel(topCat.work_hours, hoursPerDay)}</p>}
          {report.top_categories.length > 1 && (
            <ol className="mt-6 space-y-2 text-left text-white/80">
              {report.top_categories.slice(1).map((c, i) => (
                <li key={c.name} className="flex justify-between gap-4">
                  <span className="min-w-0 truncate">{i + 2}. {c.name}</span>
                  <span className="shrink-0 whitespace-nowrap font-semibold amount-blur">{formatCurrency(c.total)}</span>
                </li>
              ))}
            </ol>
          )}
        </>
      ),
    })
  }

  if (report.top_merchants.length > 0) {
    slides.push({
      key: "merchants",
      tone: "from-violet-950 via-slate-950 to-slate-900",
      content: (
        <>
          <Eyebrow>{t("wrappedSlides.laOuTuAsLe")}</Eyebrow>
          <ol className="mt-4 w-full max-w-md space-y-4 text-left">
            {report.top_merchants.map((m, i) => (
              <li key={m.merchant} className="flex items-baseline gap-3">
                <span className="w-5 shrink-0 text-lg font-black text-white/40 sm:text-xl">{i + 1}</span>
                <span className={cn("line-clamp-2 min-w-0 flex-1 break-words font-black text-white", i === 0 ? "text-xl min-[400px]:text-2xl sm:text-4xl" : "text-base sm:text-xl")}>
                  {m.merchant}
                </span>
                <span className="shrink-0 whitespace-nowrap font-semibold text-white/80 amount-blur">{formatCurrency(m.total)}</span>
              </li>
            ))}
          </ol>
        </>
      ),
    })
  }

  const big = report.biggest_expense
  if (big) {
    slides.push({
      key: "biggest",
      tone: "from-rose-950 via-slate-950 to-slate-900",
      content: (
        <>
          <Eyebrow>{t("wrappedSlides.taPlusGrosseDepense")}</Eyebrow>
          <Big>{formatCurrency(big.amount)}</Big>
          <Sub>
            {big.merchant}
            {big.category ? ` · ${big.category}` : ""}{t("wrappedSlides.biggestExpenseDate", { date: new Date(big.date).toLocaleDateString(appLocale(), { day: "numeric", month: "long" }) })}
          </Sub>
          {hoursLabel(big.work_hours, hoursPerDay) && <p className="text-white/60 amount-blur">{hoursLabel(big.work_hours, hoursPerDay)}</p>}
        </>
      ),
    })
  }

  if (report.most_expensive_month) {
    const peak = report.most_expensive_month.month
    slides.push({
      key: "months",
      tone: "from-sky-950 via-slate-950 to-slate-900",
      content: (
        <>
          <Eyebrow>{t("wrappedSlides.tonMoisLePlusCher")}</Eyebrow>
          <Big className="capitalize" blur={false}>{monthName(peak)}</Big>
          <Sub>
            <span className="font-bold text-white amount-blur">{formatCurrency(report.most_expensive_month.real_expenses)}</span> {t("wrappedSlides.expensesOf")}
            {report.thriftiest_month && (
              <>
                {t("wrappedSlides.contre")} <span className="font-bold text-white amount-blur">{formatCurrency(report.thriftiest_month.real_expenses)}</span>{t("wrappedSlides.thriftiest", { month: monthName(report.thriftiest_month.month) })}
              </>
            )}
            .
          </Sub>
          <div className="mt-6 h-40 w-full max-w-lg">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={report.months}>
                <XAxis dataKey="month" tickFormatter={monthShort} tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.05)" }}
                  labelFormatter={(m: number) => monthName(m)}
                  formatter={(v: number) => [formatCurrency(v), t("wrappedSlides.expensesLabel")]}
                  contentStyle={{ borderRadius: "12px", border: "none" }}
                />
                <Bar dataKey="real_expenses" radius={[4, 4, 0, 0]}>
                  {report.months.map((m) => (
                    <Cell key={m.month} fill={m.month === peak ? "#fb7185" : "rgba(255,255,255,0.35)"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      ),
    })
  }

  slides.push({
    key: "wealth",
    tone: "from-indigo-950 via-slate-950 to-emerald-950",
    content: (
      <>
        <Eyebrow>{t("wrappedSlides.tonPatrimoine")}</Eyebrow>
        <Big>
          {totals.net_worth_change >= 0 ? "+" : ""}
          {formatCurrency(totals.net_worth_change)}
        </Big>
        <Sub>
          <Trans t={t} i18nKey="wrappedSlides.wealthFromTo" values={{ start: formatCurrency(totals.net_worth_start), end: formatCurrency(totals.net_worth_end) }} components={{ start: <span className="amount-blur" />, end: <span className="font-bold text-white amount-blur" /> }} />
          {report.net_worth_change_pct !== null && ` (${report.net_worth_change_pct > 0 ? "+" : ""}${report.net_worth_change_pct.toLocaleString(appLocale())}${percentSuffix()})`}.
        </Sub>
        <div className="mt-6 grid grid-cols-2 gap-6 text-left">
          <div>
            <Eyebrow>{t("wrappedSlides.investiEpargne")}</Eyebrow>
            <p className="whitespace-nowrap text-xl font-black text-white min-[400px]:text-2xl amount-blur">{formatCurrency(totals.invested)}</p>
            {prev && <Delta value={prev.invested_change_pct} vsYear={prev.year} />}
          </div>
          <div>
            <Eyebrow>{t("wrappedSlides.dividendes")}</Eyebrow>
            <p className="whitespace-nowrap text-xl font-black text-white min-[400px]:text-2xl amount-blur">{formatCurrency(totals.dividends)}</p>
          </div>
        </div>
      </>
    ),
  })

  if (totals.subscriptions_cost > 0 || report.new_subscriptions.length || report.stopped_subscriptions.length) {
    slides.push({
      key: "subscriptions",
      tone: "from-fuchsia-950 via-slate-950 to-slate-900",
      content: (
        <>
          <Eyebrow>{t("wrappedSlides.tesAbonnementsTOntCoute")}</Eyebrow>
          <Big>{formatCurrency(totals.subscriptions_cost)}</Big>
          <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-6 text-left sm:grid-cols-2">
            <div>
              <Eyebrow>{t("wrappedSlides.nouveaux")}</Eyebrow>
              {report.new_subscriptions.length ? (
                <ul className="mt-2 space-y-1 text-white/80">
                  {report.new_subscriptions.slice(0, 5).map((s) => (
                    <li key={s.name}>
                      {s.name} <span className="text-white/50 amount-blur">{formatCurrency(s.monthly_cost)}{t("wrappedSlides.perMonth")}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-white/50">{t("wrappedSlides.aucun")}</p>
              )}
            </div>
            <div>
              <Eyebrow>{t("wrappedSlides.arretes")}</Eyebrow>
              {report.stopped_subscriptions.length ? (
                <>
                  <ul className="mt-2 space-y-1 text-white/80">
                    {report.stopped_subscriptions.slice(0, 5).map((s) => (
                      <li key={s.name}>{s.name}</li>
                    ))}
                  </ul>
                  <p className="mt-2 font-semibold text-emerald-400 amount-blur">
                    {t("wrappedSlides.savedPerYear", { amount: formatCurrency(report.stopped_subscriptions_yearly_saving) })}
                  </p>
                </>
              ) : (
                <p className="mt-2 text-white/50">{t("wrappedSlides.aucun")}</p>
              )}
            </div>
          </div>
        </>
      ),
    })
  }

  slides.push({
    key: "outro",
    tone: "from-slate-950 via-indigo-950 to-slate-900",
    content: (
      <>
        <Eyebrow>{t("wrappedSlides.outroTitle", { year })}</Eyebrow>
        <div className="mt-4 grid w-full max-w-lg grid-cols-2 gap-6 text-left">
          {[
            [t("wrapped.revenus"), formatCurrency(totals.income)],
            [t("wrapped.depenses"), formatCurrency(totals.real_expenses)],
            [t("wrapped.tauxDEpargne"), `${totals.savings_rate.toLocaleString(appLocale())}${percentSuffix()}`],
            [t("wrapped.patrimoine"), `${totals.net_worth_change >= 0 ? "+" : ""}${formatCurrency(totals.net_worth_change)}`],
          ].map(([label, value]) => (
            <div key={label}>
              <Eyebrow>{label}</Eyebrow>
              <p className="whitespace-nowrap text-xl font-black text-white min-[400px]:text-2xl sm:text-3xl amount-blur">{value}</p>
            </div>
          ))}
        </div>
        <Sub>{report.is_partial ? t("wrappedSlides.laSuiteAuProchainBilan") : t("wrappedSlides.outroNext", { next: year + 1 })}</Sub>
      </>
    ),
  })

  return slides
}
