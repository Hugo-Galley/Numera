import { formatCurrency } from "@/lib/utils"

/** Écart vs mois précédent. `upIsBad` : une hausse est négative (dépenses). */
export function Delta({ diff, pct, upIsBad = true }: { diff: number; pct?: number; upIsBad?: boolean }) {
  if (Math.abs(diff) < 0.5) return <span className="text-xs text-slate-400">stable</span>
  const bad = upIsBad ? diff > 0 : diff < 0
  return (
    <span className={`amount-blur text-xs font-semibold ${bad ? "text-rose-600" : "text-emerald-600"}`}>
      {diff > 0 ? "+" : "−"}
      {formatCurrency(Math.abs(diff))}
      {pct !== undefined && pct !== 0 && ` (${Math.abs(pct).toFixed(0)} %)`}
    </span>
  )
}
