import { useEffect, useState } from "react"
import { format } from "date-fns"
import { CalendarClock, Repeat } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getAnalyticsCashflowProjection } from "@/lib/api/analytics"
import { cn, formatCurrency } from "@/lib/utils"

const HORIZON_DAYS = 30
const VISIBLE = 5

interface UpcomingEvent {
  date: string
  name: string
  amount: number
  type: "scheduled" | "recurring"
  is_income: boolean
  transaction_id: number | null
  possible_duplicate: boolean
}

interface Projection {
  events: UpcomingEvent[]
  current_balance: number
  projected_balance: number
}

/** Saisies à venir et échéances récurrentes du compte, avec le solde projeté (calculé par le backend).
 * `refreshKey` change quand la liste des transactions est rechargée. */
export function UpcomingCard({ accountId, currency, refreshKey }: { accountId: number; currency: string; refreshKey: unknown }) {
  const [projection, setProjection] = useState<Projection | null>(null)
  const [failed, setFailed] = useState(false)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let cancelled = false
    setFailed(false)
    getAnalyticsCashflowProjection<Projection>(`?days=${HORIZON_DAYS}&account_id=${accountId}`)
      .then(data => { if (!cancelled) setProjection(data) })
      .catch(() => { if (!cancelled) { setProjection(null); setFailed(true) } })
    return () => { cancelled = true }
  }, [accountId, refreshKey])

  if (failed) return <p className="text-xs text-slate-400">Transactions à venir indisponibles pour le moment.</p>
  if (!projection || projection.events.length === 0) return null

  const events = expanded ? projection.events : projection.events.slice(0, VISIBLE)
  return (
    <section aria-label="À venir">
      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
          <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900">
            <CalendarClock className="h-4 w-4 text-slate-500" />
            À venir
            <Badge variant="outline" className="border-none bg-slate-100 text-slate-600">{projection.events.length}</Badge>
          </CardTitle>
          <p className="text-xs text-slate-500">
            Solde projeté à {HORIZON_DAYS} jours : <span className="font-bold text-slate-900">{formatCurrency(projection.projected_balance, currency)}</span>
          </p>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-slate-100">
            {events.map((ev, i) => (
              <li key={`${ev.type}-${ev.transaction_id ?? ev.date}-${i}`} className="flex items-center gap-3 py-2 text-sm">
                <span className="w-12 shrink-0 text-xs text-slate-400">{format(new Date(ev.date), "dd/MM")}</span>
                <span className="flex min-w-0 flex-1 items-center gap-1.5">
                  <span className="truncate font-medium text-slate-900">{ev.name}</span>
                  {ev.type === "recurring" && (
                    <Badge variant="outline" className="gap-1 border-none bg-indigo-50 px-1.5 py-0 text-[10px] text-indigo-700"><Repeat className="h-3 w-3" />Récurrent</Badge>
                  )}
                  {ev.possible_duplicate && (
                    <Badge variant="outline" className="border-none bg-amber-50 px-1.5 py-0 text-[10px] text-amber-700">Doublon possible</Badge>
                  )}
                </span>
                <span className={cn("shrink-0 font-bold", ev.is_income ? "text-emerald-600" : "text-rose-600")}>
                  {ev.is_income ? "+" : "−"}{formatCurrency(ev.amount, currency)}
                </span>
              </li>
            ))}
          </ul>
          {projection.events.length > VISIBLE && (
            <Button variant="ghost" size="sm" className="mt-1 h-9 w-full text-xs text-slate-500" onClick={() => setExpanded(e => !e)}>
              {expanded ? "Réduire" : `Voir les ${projection.events.length} échéances`}
            </Button>
          )}
        </CardContent>
      </Card>
    </section>
  )
}
