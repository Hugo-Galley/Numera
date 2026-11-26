import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { Slice } from "./slices"

interface BreakdownLegendProps {
  slices: Slice[]
  active: number | null
  onHover: (index: number | null) => void
  /** Logo de la société devant le nom (entreprises et positions) */
  withLogos: boolean
}

/** Légende du donut : une ligne par part (nom, part du compte, montant), survol relié au graphique. */
export function BreakdownLegend({ slices, active, onHover, withLogos }: BreakdownLegendProps) {
  return (
    <ul className="divide-y divide-slate-100">
      {slices.map((s, i) => (
        <li
          key={s.key}
          onMouseEnter={() => onHover(i)}
          onMouseLeave={() => onHover(null)}
          className={`grid grid-cols-[10px_minmax(0,1fr)_auto_auto] items-center gap-2 py-1.5 text-sm transition-opacity ${
            active !== null && active !== i ? "opacity-50" : ""
          }`}
        >
          <span className="h-2.5 w-2.5 rounded-xs" style={{ backgroundColor: s.color }} aria-hidden="true" />
          <span className="flex min-w-0 items-center gap-1.5">
            {withLogos && !s.isOther && <CompanyLogo ticker={s.ticker} name={s.name} className="h-4 w-4 shrink-0 rounded-xs" />}
            <span className="truncate text-slate-700" title={s.name}>{s.name}</span>
          </span>
          <span className="text-right text-xs text-slate-500 tabular-nums sm:w-14">{formatRate(s.share, 1)}</span>
          <span className="text-right font-semibold text-slate-900 tabular-nums sm:w-24">{formatCurrency(s.value)}</span>
        </li>
      ))}
    </ul>
  )
}
