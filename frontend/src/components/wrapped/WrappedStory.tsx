import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react"
import { ChevronLeft, ChevronRight, X } from "lucide-react"
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from "recharts"
import { cn, formatCurrency } from "@/lib/utils"
import { useWorkTime } from "@/providers/WorkTimeProvider"
import type { WrappedReport } from "@/types/wrapped"
import { Delta, hoursLabel, monthName, monthShort } from "./format"

interface Slide {
  key: string
  /** Dégradé de fond de la carte */
  tone: string
  content: ReactNode
}

function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-xs font-bold uppercase tracking-[0.2em] text-white/60 sm:text-sm">{children}</p>
}

function Big({ children, className, blur = true }: { children: ReactNode; className?: string; blur?: boolean }) {
  return <p className={cn("break-words text-4xl font-black tracking-tight text-white min-[400px]:text-5xl sm:text-7xl", blur && "amount-blur", className)}>{children}</p>
}

function Sub({ children }: { children: ReactNode }) {
  return <p className="text-base text-white/80 min-[400px]:text-lg sm:text-xl">{children}</p>
}

function buildSlides(report: WrappedReport, hoursPerDay: number): Slide[] {
  const { totals, previous: prev, year } = report
  const period = report.is_partial ? `de janvier à ${monthName(report.months_covered)}` : "de janvier à décembre"
  const slides: Slide[] = []

  slides.push({
    key: "intro",
    tone: "from-slate-950 via-indigo-950 to-slate-900",
    content: (
      <>
        <Eyebrow>Ton bilan</Eyebrow>
        <Big className="sm:text-8xl" blur={false}>{year}</Big>
        <Sub>
          {period}, {totals.expense_count.toLocaleString("fr-FR")} dépenses passées au crible.
        </Sub>
      </>
    ),
  })

  slides.push({
    key: "flows",
    tone: "from-emerald-950 via-slate-950 to-slate-900",
    content: (
      <>
        <Eyebrow>Ce qui est entré</Eyebrow>
        <Big>{formatCurrency(totals.income)}</Big>
        {prev && <Delta value={prev.income_change_pct} vsYear={prev.year} />}
        <div className="mt-6 space-y-2">
          <Eyebrow>Ce qui est sorti</Eyebrow>
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
        <Eyebrow>Tu as mis de côté</Eyebrow>
        <Big className="sm:text-8xl">{totals.savings_rate.toLocaleString("fr-FR")} %</Big>
        <Sub>
          de tes revenus, soit <span className="font-bold text-white amount-blur">{formatCurrency(totals.saved)}</span>.
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
          <Eyebrow>Ton plus gros poste</Eyebrow>
          <Big blur={false}>{topCat.name}</Big>
          <Sub>
            <span className="font-bold text-white amount-blur">{formatCurrency(topCat.total)}</span>, {topCat.percentage.toLocaleString("fr-FR")} % de tes dépenses.
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
          <Eyebrow>Là où tu as le plus dépensé</Eyebrow>
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
          <Eyebrow>Ta plus grosse dépense</Eyebrow>
          <Big>{formatCurrency(big.amount)}</Big>
          <Sub>
            {big.merchant}
            {big.category ? ` · ${big.category}` : ""}, le {new Date(big.date).toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}.
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
          <Eyebrow>Ton mois le plus cher</Eyebrow>
          <Big className="capitalize" blur={false}>{monthName(peak)}</Big>
          <Sub>
            <span className="font-bold text-white amount-blur">{formatCurrency(report.most_expensive_month.real_expenses)}</span> de dépenses
            {report.thriftiest_month && (
              <>
                , contre <span className="font-bold text-white amount-blur">{formatCurrency(report.thriftiest_month.real_expenses)}</span> en {monthName(report.thriftiest_month.month)}, ton mois le plus sobre
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
                  formatter={(v: number) => [formatCurrency(v), "Dépenses"]}
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
        <Eyebrow>Ton patrimoine</Eyebrow>
        <Big>
          {totals.net_worth_change >= 0 ? "+" : ""}
          {formatCurrency(totals.net_worth_change)}
        </Big>
        <Sub>
          de <span className="amount-blur">{formatCurrency(totals.net_worth_start)}</span> à{" "}
          <span className="font-bold text-white amount-blur">{formatCurrency(totals.net_worth_end)}</span>
          {report.net_worth_change_pct !== null && ` (${report.net_worth_change_pct > 0 ? "+" : ""}${report.net_worth_change_pct.toLocaleString("fr-FR")} %)`}.
        </Sub>
        <div className="mt-6 grid grid-cols-2 gap-6 text-left">
          <div>
            <Eyebrow>Investi / épargné</Eyebrow>
            <p className="whitespace-nowrap text-xl font-black text-white min-[400px]:text-2xl amount-blur">{formatCurrency(totals.invested)}</p>
            {prev && <Delta value={prev.invested_change_pct} vsYear={prev.year} />}
          </div>
          <div>
            <Eyebrow>Dividendes</Eyebrow>
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
          <Eyebrow>Tes abonnements t'ont coûté</Eyebrow>
          <Big>{formatCurrency(totals.subscriptions_cost)}</Big>
          <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-6 text-left sm:grid-cols-2">
            <div>
              <Eyebrow>Nouveaux</Eyebrow>
              {report.new_subscriptions.length ? (
                <ul className="mt-2 space-y-1 text-white/80">
                  {report.new_subscriptions.slice(0, 5).map((s) => (
                    <li key={s.name}>
                      {s.name} <span className="text-white/50 amount-blur">{formatCurrency(s.monthly_cost)}/mois</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-white/50">Aucun</p>
              )}
            </div>
            <div>
              <Eyebrow>Arrêtés</Eyebrow>
              {report.stopped_subscriptions.length ? (
                <>
                  <ul className="mt-2 space-y-1 text-white/80">
                    {report.stopped_subscriptions.slice(0, 5).map((s) => (
                      <li key={s.name}>{s.name}</li>
                    ))}
                  </ul>
                  <p className="mt-2 font-semibold text-emerald-400 amount-blur">
                    {formatCurrency(report.stopped_subscriptions_yearly_saving)} économisés par an
                  </p>
                </>
              ) : (
                <p className="mt-2 text-white/50">Aucun</p>
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
        <Eyebrow>{year} en un coup d'œil</Eyebrow>
        <div className="mt-4 grid w-full max-w-lg grid-cols-2 gap-6 text-left">
          {[
            ["Revenus", formatCurrency(totals.income)],
            ["Dépenses", formatCurrency(totals.real_expenses)],
            ["Taux d'épargne", `${totals.savings_rate.toLocaleString("fr-FR")} %`],
            ["Patrimoine", `${totals.net_worth_change >= 0 ? "+" : ""}${formatCurrency(totals.net_worth_change)}`],
          ].map(([label, value]) => (
            <div key={label}>
              <Eyebrow>{label}</Eyebrow>
              <p className="whitespace-nowrap text-xl font-black text-white min-[400px]:text-2xl sm:text-3xl amount-blur">{value}</p>
            </div>
          ))}
        </div>
        <Sub>{report.is_partial ? "La suite au prochain bilan." : `À l'année prochaine pour ${year + 1}.`}</Sub>
      </>
    ),
  })

  return slides
}

interface WrappedStoryProps {
  report: WrappedReport
  onClose: () => void
}

/** Bilan en plein écran, une carte par chiffre clé (clic, flèches du clavier, Échap pour fermer). */
export function WrappedStory({ report, onClose }: WrappedStoryProps) {
  const { workTime } = useWorkTime()
  const slides = useMemo(() => buildSlides(report, workTime?.work_hours_per_day ?? 7), [report, workTime])
  const [index, setIndex] = useState(0)
  const last = slides.length - 1

  const next = useCallback(() => {
    if (index >= last) onClose()
    else setIndex((i) => i + 1)
  }, [index, last, onClose])
  const prev = useCallback(() => setIndex((i) => Math.max(0, i - 1)), [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault()
        next()
      } else if (e.key === "ArrowLeft") prev()
      else if (e.key === "Escape") onClose()
    }
    document.addEventListener("keydown", onKey)
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", onKey)
      document.body.style.overflow = ""
    }
  }, [next, prev, onClose])

  const slide = slides[index]

  return (
    <div className={cn("fixed inset-0 z-50 flex h-dvh flex-col overflow-hidden bg-gradient-to-br transition-colors duration-500", slide.tone)}>
      <div className="flex items-center gap-1.5 px-4 pt-[max(1rem,env(safe-area-inset-top))] sm:px-8">
        {slides.map((s, i) => (
          <button
            key={s.key}
            aria-label={`Carte ${i + 1}`}
            onClick={() => setIndex(i)}
            className={cn("relative h-1 flex-1 rounded-full transition-colors before:absolute before:-inset-y-3 before:inset-x-0 before:content-['']", i <= index ? "bg-white" : "bg-white/25")}
          />
        ))}
        <button onClick={onClose} aria-label="Fermer" className="-my-2 ml-2 flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-white/70 hover:bg-white/10 hover:text-white">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="relative flex flex-1 items-center justify-center overflow-y-auto overflow-x-hidden px-5 py-6 sm:px-6 sm:py-8">
        {/* Zones de navigation : tiers gauche = précédent, le reste = suivant */}
        <button aria-label="Précédent" onClick={prev} className="absolute inset-y-0 left-0 w-1/3 cursor-w-resize" />
        <button aria-label="Suivant" onClick={next} className="absolute inset-y-0 right-0 w-2/3 cursor-e-resize" />
        <div
          key={slide.key}
          className="pointer-events-none relative flex w-full max-w-2xl flex-col items-center gap-3 text-center wrapped-enter [&_.recharts-wrapper]:pointer-events-auto"
        >
          {slide.content}
        </div>
      </div>

      <div className="flex items-center justify-between px-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:px-8 sm:pb-6">
        <button onClick={prev} disabled={index === 0} className="flex h-12 w-12 items-center justify-center rounded-full text-white/70 hover:bg-white/10 disabled:opacity-0" aria-label="Précédent">
          <ChevronLeft className="h-6 w-6" />
        </button>
        <span className="text-xs font-semibold text-white/50">
          {index + 1} / {slides.length}
        </span>
        <button onClick={next} className="flex h-12 w-12 items-center justify-center rounded-full text-white/70 hover:bg-white/10" aria-label={index === last ? "Terminer" : "Suivant"}>
          <ChevronRight className="h-6 w-6" />
        </button>
      </div>
    </div>
  )
}
