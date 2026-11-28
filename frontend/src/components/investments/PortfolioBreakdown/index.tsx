import { lazy, Suspense, useState } from "react"
import { useTranslation } from "react-i18next"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { PieChart as PieChartIcon } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useIsMobile } from "@/hooks/useIsMobile"
import { keepSeriesOrder, numberFormatter } from "@/lib/chartTooltip"
import { formatCurrency, formatRate } from "@/lib/utils"
import { BreakdownLegend } from "./BreakdownLegend"
import { hasSourceChoice, rowsFor, totalFor, viewsFor, type BreakdownData, type BreakdownSource, type BreakdownView } from "./rows"
import { buildSlices } from "./slices"

// react-simple-maps et le fond de carte ne se chargent qu'à l'ouverture de la carte
const WorldMap = lazy(() => import("@/components/ui/WorldMap"))
const DISPLAYS = ["chart", "map"] as const
type Display = (typeof DISPLAYS)[number]

export type { BreakdownData } from "./rows"

interface PortfolioBreakdownProps {
  data: BreakdownData
  /** Un compte (« du compte ») ou tous les comptes d'investissement (« du portefeuille ») */
  scope: "account" | "portfolio"
}

const SOURCES: BreakdownSource[] = ["all", "direct", "etf"]

function Segmented<T extends string>({ label, options, value, onChange, render }: {
  label: string
  options: T[]
  value: T
  onChange: (v: T) => void
  render: (v: T) => string
}) {
  return (
    <div role="group" aria-label={label} className="grid w-full grid-cols-2 items-center gap-1 rounded-lg bg-slate-100 p-1 sm:flex sm:w-auto">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          aria-pressed={value === o}
          onClick={() => onChange(o)}
          className={`min-h-10 rounded-md px-2 py-1 text-xs font-semibold transition-all sm:min-h-8 sm:px-3 ${
            value === o ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-700"
          }`}
        >
          {render(o)}
        </button>
      ))}
    </div>
  )
}

/**
 * Donut de répartition des positions : entreprises réellement détenues (ETF décomposés), positions, secteurs, pays ;
 * pour les entreprises et les positions, choix de la provenance (tout, en direct, via ETF).
 */
export function PortfolioBreakdown({ data, scope }: PortfolioBreakdownProps) {
  const { t } = useTranslation("investments")
  const isMobile = useIsMobile()
  const [view, setView] = useState<BreakdownView>("companies")
  const [source, setSource] = useState<BreakdownSource>("all")
  const [hideOther, setHideOther] = useState(false)
  const [active, setActive] = useState<number | null>(null)
  const [display, setDisplay] = useState<Display>("chart")

  const base = data.totals.stocks_eur
  if (base <= 0) return null

  const views = viewsFor(data)
  const current = views.includes(view) ? view : "companies"
  const sourceChoice = hasSourceChoice(data, current)
  const currentSource = sourceChoice ? source : "all"
  const total = totalFor(data, currentSource)
  const all = buildSlices(rowsFor(data, current, currentSource), total, t(`breakdown.other.${current}`), base)
  const canHideOther = all.some((s) => s.isOther) && all.some((s) => !s.isOther)
  const slices = hideOther && canHideOther ? all.filter((s) => !s.isOther) : all
  const hovered = active !== null ? slices[active] : undefined
  const shown = slices.reduce((sum, s) => sum + s.value, 0)
  const share = (value: number) => t(`breakdown.shareOf.${scope}`, { share: formatRate((value / base) * 100, 1) })

  const center = hovered
    ? { label: hovered.name, value: hovered.value, hint: share(hovered.value) }
    : hideOther && canHideOther
      ? { label: t("breakdown.namedLines"), value: shown, hint: share(shown) }
      : currentSource !== "all"
        ? { label: t(`breakdown.center.${currentSource}`), value: total, hint: share(total) }
        : { label: t("breakdown.center.all"), value: base, hint: t("breakdown.positionsCount", { count: data.totals.holdings_count }) }

  const showMap = current === "countries" && display === "map"
  const reset = () => setActive(null)
  // Écart sous 1 € : arrondis, pas d'argent hors positions
  const outside = data.totals.outside_positions_eur ?? 0
  const reconcile = currentSource === "all" && data.totals.accounts_eur !== undefined && Math.abs(outside) >= 1

  return (
    <Card className="shadow-xs">
      <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <PieChartIcon className="h-4 w-4 text-slate-500" />
            <CardTitle className="text-lg">{t(`breakdown.title.${scope}`)}</CardTitle>
          </div>
          <CardDescription>{t(`breakdown.description.${scope}`)}</CardDescription>
        </div>
        <div className="flex flex-col gap-2 sm:items-end">
          {views.length > 1 && (
            <Segmented label={t("breakdown.viewsLabel")} options={views} value={current} render={(v) => t(`breakdown.views.${v}`)}
              onChange={(v) => { setView(v); reset() }} />
          )}
          {current === "countries" && (
            <Segmented label={t("breakdown.displayLabel")} options={[...DISPLAYS]} value={display} render={(d) => t(`breakdown.display.${d}`)}
              onChange={setDisplay} />
          )}
        </div>
      </CardHeader>
      {showMap ? (
        <CardContent className="relative h-[300px] p-0 md:h-[450px]">
          <Suspense fallback={<div className="h-full animate-pulse bg-slate-50" />}>
            <WorldMap data={data.countries.map((c) => ({ name: c.name, value: c.value_eur, percentage: (c.value_eur / base) * 100 }))} />
          </Suspense>
        </CardContent>
      ) : (
      <CardContent className="grid items-center gap-6 md:grid-cols-[minmax(0,280px)_minmax(0,1fr)]">
        <div className="relative h-[240px] md:h-[280px]" role="img" aria-label={t("breakdown.chartLabel")}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
              <Pie
                data={slices}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={isMobile ? 70 : 84}
                outerRadius={isMobile ? 100 : 120}
                paddingAngle={slices.length > 1 ? 1.5 : 0}
                stroke="none"
                isAnimationActive={false}
                onMouseEnter={(_, index) => setActive(index)}
                onMouseLeave={reset}
              >
                {slices.map((s, i) => (
                  <Cell key={s.key} fill={s.color} fillOpacity={active === null || active === i ? 1 : 0.35} />
                ))}
              </Pie>
              <Tooltip
                itemSorter={keepSeriesOrder}
                formatter={numberFormatter((v: number) => `${formatCurrency(v)} · ${formatRate((v / base) * 100, 1)}`)}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-16 text-center">
            <span className="max-w-full truncate text-xs font-semibold text-slate-500">{center.label}</span>
            <span className="text-lg font-black text-slate-900 md:text-xl">{formatCurrency(center.value)}</span>
            <span className="text-xs text-slate-500">{center.hint}</span>
          </div>
        </div>
        <div className="min-w-0 space-y-3">
          {sourceChoice && (
            <Segmented label={t("breakdown.sourcesLabel")} options={SOURCES} value={currentSource} render={(s) => t(`breakdown.sources.${s}`)}
              onChange={(s) => { setSource(s); reset() }} />
          )}
          <BreakdownLegend slices={slices} active={active} onHover={setActive} withLogos={current === "companies" || current === "positions"} />
          {reconcile && (
            <dl className="space-y-1 border-t border-slate-200 pt-2 text-sm">
              <div className="flex items-baseline justify-between gap-2">
                <dt className="text-slate-500">{t("breakdown.outsidePositions")}</dt>
                <dd className="font-semibold text-slate-700 tabular-nums amount-blur">{formatCurrency(outside)}</dd>
              </div>
              <div className="flex items-baseline justify-between gap-2">
                <dt className="text-slate-500">{t("breakdown.accountsValue")}</dt>
                <dd className="font-bold text-slate-900 tabular-nums amount-blur">{formatCurrency(data.totals.accounts_eur ?? 0)}</dd>
              </div>
              <p className="text-xs text-slate-400">{t("breakdown.outsidePositionsHint")}</p>
            </dl>
          )}
          {canHideOther && (
            <label className="flex min-h-10 cursor-pointer items-center gap-2 text-xs text-slate-500">
              <input type="checkbox" className="h-4 w-4" checked={hideOther} onChange={(e) => { setHideOther(e.target.checked); reset() }} />
              {t("breakdown.hideOther")}
            </label>
          )}
        </div>
      </CardContent>
      )}
    </Card>
  )
}
