import { useId } from "react"
import { useTranslation } from "react-i18next"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { buildSlices } from "@/components/investments/PortfolioBreakdown/slices"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { keepSeriesOrder, numberFormatter } from "@/lib/chartTooltip"
import { countryName } from "@/lib/countries"
import { formatRate } from "@/lib/utils"
import type { EtfWeight } from "./types"

function WeightsDonut({ title, otherLabel, rows }: { title: string; otherLabel: string; rows: { name: string; weight: number }[] }) {
  const titleId = useId()
  // En % du fonds ; une part négative (dérivés) ne se dessine pas
  const total = rows.reduce((sum, r) => sum + Math.max(r.weight, 0), 0)
  const slices = buildSlices(rows.map((r) => ({ name: r.name, value: r.weight })), total, otherLabel, 100)
  if (slices.length === 0) return null
  return (
    <section aria-labelledby={titleId} className="min-w-0">
      <Card className="h-full shadow-xs">
        <CardHeader className="pb-2">
          <CardTitle id={titleId} className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent className="grid items-center gap-4 sm:grid-cols-[180px_minmax(0,1fr)]">
          <div className="h-[180px]" aria-hidden="true">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <Pie data={slices} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={52} outerRadius={84}
                  paddingAngle={slices.length > 1 ? 1.5 : 0} stroke="none" isAnimationActive={false}>
                  {slices.map((s) => <Cell key={s.key} fill={s.color} />)}
                </Pie>
                <Tooltip itemSorter={keepSeriesOrder} formatter={numberFormatter((v: number) => formatRate(v, 1))} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="min-w-0 divide-y divide-slate-100">
            {slices.map((s) => (
              <li key={s.key} className="grid grid-cols-[10px_minmax(0,1fr)_auto] items-center gap-2 py-1.5 text-sm">
                <span className="h-2.5 w-2.5 rounded-xs" style={{ backgroundColor: s.color }} aria-hidden="true" />
                <span className="truncate text-slate-700" title={s.name}>{s.name}</span>
                <span className="text-right text-xs font-semibold text-slate-900 tabular-nums">{formatRate(s.share, 1)}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </section>
  )
}

/** Répartitions du fonds par pays et par secteur. */
export function Weights({ countries, sectors }: { countries: EtfWeight[]; sectors: EtfWeight[] }) {
  const { t } = useTranslation("etfSheet")
  if (countries.length === 0 && sectors.length === 0) return null
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <WeightsDonut title={t("weights.countries")} otherLabel={t("weights.otherCountries")}
        rows={countries.map((c) => ({ name: countryName(c.name), weight: c.weight }))} />
      <WeightsDonut title={t("weights.sectors")} otherLabel={t("weights.otherSectors")} rows={sectors} />
    </div>
  )
}
