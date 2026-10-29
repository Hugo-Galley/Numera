import { AlertTriangle, CheckCircle2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCurrency, formatRate } from "@/lib/utils"
import { KIND_LABELS, WrapperCard } from "./types"

export function Money({ value }: { value: number }) {
  return <span className="amount-blur whitespace-nowrap tabular-nums">{formatCurrency(value)}</span>
}

export function Gauge({ pct }: { pct: number }) {
  const color = pct > 100 ? "bg-rose-500" : pct > 90 ? "bg-amber-500" : "bg-emerald-500"
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  )
}

export function WrapperCardView({ card }: { card: WrapperCard }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-start justify-between gap-3 text-base">
          <span className="min-w-0 break-words">{card.account_name}</span>
          <span className="shrink-0 pt-0.5 text-xs font-semibold uppercase tracking-wider text-slate-500">{KIND_LABELS[card.kind]}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {card.ceiling !== null && card.current !== null && (
          <div className="space-y-2">
            <Gauge pct={card.used_pct ?? 0} />
            <div className="flex flex-wrap justify-between gap-x-3">
              <span><Money value={card.current} /> sur <Money value={card.ceiling} /></span>
              <span className="text-slate-500">{formatRate(card.used_pct ?? 0, 1)}</span>
            </div>
            <div className="text-slate-600">
              Place restante : <strong><Money value={card.remaining ?? 0} /></strong>
            </div>
          </div>
        )}
        {card.milestone_years !== null && (
          <div className="flex items-center gap-2">
            {card.milestone_reached && <CheckCircle2 className="h-4 w-4 text-emerald-600" />}
            {card.age_years !== null ? (
              <span>
                Ancienneté : {card.age_years.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} an(s) / {card.milestone_years} ans
                {card.milestone_reached ? " — atteint" : ""}
              </span>
            ) : (
              <span className="text-slate-500">Ancienneté inconnue (seuil : {card.milestone_years} ans)</span>
            )}
          </div>
        )}
        {card.estimated_tax_saving !== null && (
          <div>Économie d'impôt estimée : <strong><Money value={card.estimated_tax_saving} /></strong></div>
        )}
        {card.allowance !== null && (
          <div>Abattement annuel sur les gains de rachat : <strong><Money value={card.allowance} /></strong></div>
        )}
        {card.total_contributed !== null && (
          <div className="space-y-1">
            <div>Total versé : <strong><Money value={card.total_contributed} /></strong></div>
            <div>Disponible : <strong><Money value={card.available ?? 0} /></strong></div>
            <div>
              Bloqué (moins de 5 ans) : <strong><Money value={card.blocked ?? 0} /></strong>
              {card.next_unlock_date && (
                <span className="text-slate-500"> — prochain déblocage le {new Date(card.next_unlock_date).toLocaleDateString("fr-FR")}</span>
              )}
            </div>
          </div>
        )}
        {card.alerts.map((alert) => (
          <div key={alert} className="flex items-start gap-2 rounded-md bg-amber-50 p-2 text-amber-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{alert}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
