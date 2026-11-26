import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { PieChart as PieChartIcon } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorState } from "@/components/layout/ErrorState"
import { useIsMobile } from "@/hooks/useIsMobile"
import { getAnalyticsDiversityScanner } from "@/lib/api/analytics"
import type { ApiResponse } from "@/lib/api/types"
import { resetApiCache } from "@/lib/apiCache"
import { keepSeriesOrder, numberFormatter } from "@/lib/chartTooltip"
import { countryName } from "@/lib/countries"
import { formatCurrency, formatRate } from "@/lib/utils"
import { BreakdownLegend } from "./BreakdownLegend"
import { buildSlices, type BreakdownRow } from "./slices"

type Scanner = ApiResponse<"/analytics/diversity-scanner", "get">
type View = "companies" | "positions" | "sectors" | "countries"

interface AccountBreakdownProps {
  accountId: number
  /** Change à chaque rechargement des données du compte : relance le calcul */
  reloadKey?: unknown
}

function rowsFor(data: Scanner, view: View): BreakdownRow[] {
  switch (view) {
    case "companies":
      return data.top_underlying_companies.map((c) => ({ name: c.name, value: c.total_value_eur, ticker: c.ticker }))
    case "positions":
      return data.holdings.map((h) => ({ name: h.name || h.ticker, value: h.value_eur, ticker: h.ticker }))
    case "sectors":
      return data.sectors.map((s) => ({ name: s.name, value: s.value_eur }))
    case "countries":
      // « Autres » / « Non renseigné » restent tels quels et sont regroupés dans la part « Autres pays »
      return data.countries.map((c) => ({ name: countryName(c.name), value: c.value_eur }))
  }
}

/** Vues proposées : secteurs et pays n'ont de sens qu'avec un ETF décomposé, les positions qu'à partir de deux lignes. */
function viewsFor(data: Scanner): View[] {
  const views: View[] = ["companies"]
  if (data.holdings.length > 1) views.push("positions")
  if (data.totals.etfs_count > 0) views.push("sectors", "countries")
  return views
}

/** Donut de répartition d'un compte d'investissement : entreprises détenues (ETF décomposés), positions, secteurs, pays. */
export function AccountBreakdown({ accountId, reloadKey }: AccountBreakdownProps) {
  const { t } = useTranslation("investments")
  const isMobile = useIsMobile()
  const [data, setData] = useState<Scanner | null>(null)
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading")
  const [attempt, setAttempt] = useState(0)
  const [view, setView] = useState<View>("companies")
  const [hideOther, setHideOther] = useState(false)
  const [active, setActive] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    setStatus("loading")
    getAnalyticsDiversityScanner(`?account_id=${accountId}`)
      .then((res) => {
        if (cancelled) return
        setData(res)
        setStatus("ready")
      })
      .catch(() => !cancelled && setStatus("error"))
    return () => {
      cancelled = true
    }
  }, [accountId, reloadKey, attempt])

  if (status === "loading" && !data) return <Skeleton className="h-72 w-full rounded-xl" />
  if (status === "error") {
    return <ErrorState message={t("accountBreakdown.loadFailed")} onRetry={() => { resetApiCache(); setAttempt((n) => n + 1) }} />
  }
  if (!data || data.totals.stocks_eur <= 0) return null

  const views = viewsFor(data)
  const current = views.includes(view) ? view : "companies"
  const total = data.totals.stocks_eur
  const all = buildSlices(rowsFor(data, current), total, t(`accountBreakdown.other.${current}`))
  const canHideOther = all.some((s) => s.isOther) && all.some((s) => !s.isOther)
  const slices = hideOther && canHideOther ? all.filter((s) => !s.isOther) : all
  const hovered = active !== null ? slices[active] : undefined
  const shown = slices.reduce((sum, s) => sum + s.value, 0)

  const center = hovered
    ? { label: hovered.name, value: formatCurrency(hovered.value), hint: t("accountBreakdown.shareOfAccount", { share: formatRate(hovered.share, 1) }) }
    : hideOther && canHideOther
      ? { label: t("accountBreakdown.namedLines"), value: formatCurrency(shown), hint: t("accountBreakdown.shareOfAccount", { share: formatRate((shown / total) * 100, 1) }) }
      : { label: t("accountBreakdown.centerTotal"), value: formatCurrency(total), hint: t("accountBreakdown.positionsCount", { count: data.totals.holdings_count }) }

  return (
    <Card className="shadow-xs">
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <PieChartIcon className="h-4 w-4 text-slate-500" />
            <CardTitle className="text-lg">{t("accountBreakdown.title")}</CardTitle>
          </div>
          <CardDescription>{t("accountBreakdown.description")}</CardDescription>
        </div>
        {views.length > 1 && (
          <div
            role="group"
            aria-label={t("accountBreakdown.viewsLabel")}
            className="grid w-full shrink-0 grid-cols-2 items-center gap-1 rounded-lg bg-slate-100 p-1 sm:flex sm:w-auto"
          >
            {views.map((v) => (
              <button
                key={v}
                type="button"
                aria-pressed={current === v}
                onClick={() => { setView(v); setActive(null) }}
                className={`min-h-10 rounded-md px-2 py-1 text-xs font-semibold transition-all sm:min-h-8 sm:px-3 ${
                  current === v ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                {t(`accountBreakdown.views.${v}`)}
              </button>
            ))}
          </div>
        )}
      </CardHeader>
      <CardContent className="grid items-center gap-6 md:grid-cols-[minmax(0,280px)_minmax(0,1fr)]">
        <div className="relative h-[240px] md:h-[280px]" role="img" aria-label={t("accountBreakdown.chartLabel")}>
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
                onMouseLeave={() => setActive(null)}
              >
                {slices.map((s, i) => (
                  <Cell key={s.key} fill={s.color} fillOpacity={active === null || active === i ? 1 : 0.35} />
                ))}
              </Pie>
              <Tooltip
                itemSorter={keepSeriesOrder}
                formatter={numberFormatter((v: number) => `${formatCurrency(v)} · ${formatRate((v / total) * 100, 1)}`)}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-16 text-center">
            <span className="max-w-full truncate text-xs font-semibold text-slate-500">{center.label}</span>
            <span className="text-lg font-black text-slate-900 md:text-xl">{center.value}</span>
            <span className="text-xs text-slate-500">{center.hint}</span>
          </div>
        </div>
        <div className="min-w-0 space-y-3">
          <BreakdownLegend slices={slices} active={active} onHover={setActive} withLogos={current === "companies" || current === "positions"} />
          {canHideOther && (
            <label className="flex min-h-10 cursor-pointer items-center gap-2 text-xs text-slate-500">
              <input type="checkbox" className="h-4 w-4" checked={hideOther} onChange={(e) => { setHideOther(e.target.checked); setActive(null) }} />
              {t("accountBreakdown.hideOther")}
            </label>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
