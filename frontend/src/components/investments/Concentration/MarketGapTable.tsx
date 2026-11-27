import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { MarketComparison, MarketDimensionKey } from "@/types/diversity"
import { formatRate } from "@/lib/utils"
import { formatPoints } from "./format"

const DIMENSIONS: MarketDimensionKey[] = ["sectors", "countries", "companies"]
const MAX_ROWS = 8

/** Tableau « toi contre le marché » d'une dimension : double barre et écart en points. */
export function MarketGapTable({ market }: { market: MarketComparison }) {
  const { t } = useTranslation("investments")
  const [dimension, setDimension] = useState<MarketDimensionKey>("sectors")
  const current = market[dimension]
  // Présentation : les plus gros écarts, dans un sens ou dans l'autre
  const rows = [...(current?.rows ?? [])].sort((a, b) => Math.abs(b.gap_pts) - Math.abs(a.gap_pts)).slice(0, MAX_ROWS)
  const scale = Math.max(1, ...rows.flatMap((r) => [r.portfolio_pct, r.market_pct]))

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">{t("concentration.table.title")}</h3>
        <div role="group" aria-label={t("concentration.table.dimension")} className="flex gap-1 rounded-lg bg-slate-100 p-1">
          {DIMENSIONS.map((d) => (
            <button
              key={d}
              type="button"
              aria-pressed={dimension === d}
              onClick={() => setDimension(d)}
              className={`min-h-10 rounded-md px-3 py-1 text-xs font-semibold sm:min-h-8 ${dimension === d ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-700"}`}
            >
              {t(`concentration.dimensions.${d}`)}
            </button>
          ))}
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500">{t("concentration.table.empty")}</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-slate-500">
              <th className="py-2 pr-2 font-medium">{t("concentration.table.line")}</th>
              <th className="hidden w-1/3 py-2 pr-2 font-medium sm:table-cell"><span className="sr-only">{t("concentration.table.you")} / {t("concentration.table.market")}</span></th>
              <th className="py-2 pr-2 text-right font-medium">{t("concentration.table.you")}</th>
              <th className="py-2 pr-2 text-right font-medium">{t("concentration.table.market")}</th>
              <th className="py-2 text-right font-medium">{t("concentration.table.gap")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.name} className="border-b last:border-0">
                <td className="py-2 pr-2 font-medium text-slate-900">{row.name}</td>
                <td className="hidden py-2 pr-2 sm:table-cell" aria-hidden="true">
                  <div className="space-y-1">
                    <div className="h-1.5 rounded-full bg-slate-900" style={{ width: `${(row.portfolio_pct / scale) * 100}%` }} />
                    <div className="h-1.5 rounded-full bg-slate-300" style={{ width: `${(row.market_pct / scale) * 100}%` }} />
                  </div>
                </td>
                <td className="py-2 pr-2 text-right tabular-nums">{formatRate(row.portfolio_pct, 0)}</td>
                <td className="py-2 pr-2 text-right tabular-nums text-slate-600" title={row.market_pct_is_upper_bound ? t("concentration.table.upperBound") : undefined}>
                  {row.market_pct_is_upper_bound ? "≤ " : ""}{formatRate(row.market_pct, row.market_pct < 1 ? 1 : 0)}
                </td>
                <td className={`py-2 text-right font-semibold tabular-nums ${row.gap_pts > 0 ? "text-amber-700" : "text-slate-500"}`}>
                  {t("concentration.table.gapPts", { value: formatPoints(row.gap_pts) })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="text-xs text-slate-500">
        {t("concentration.activeShare")} ({t(`concentration.dimensions.${dimension}`)}) : {formatRate(current?.active_share_pct, 0)}
      </p>
    </div>
  )
}
