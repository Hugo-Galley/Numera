import { AlertTriangle, CheckCircle2, Pencil, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { format, parseISO } from "date-fns"
import { formatCurrency } from "@/lib/utils"
import { fr } from "date-fns/locale"

export interface Provision {
  id: number
  name: string
  amount: number
  interval_months: number
  due_date: string
  category_id: number | null
  account_id: number | null
  note: string | null
  active: boolean
  category_name: string | null
  account_name: string | null
  next_due: string
  previous_due: string
  months_left: number
  monthly_amount: number
  target_now: number
  monthly_needed: number
  funded: number | null
  status: "on_track" | "behind" | "untracked" | "inactive"
  last_payment: { date: string; amount: number } | null
}

export const INTERVALS: { value: string; label: string }[] = [
  { value: "1", label: "Mensuelle" },
  { value: "3", label: "Trimestrielle" },
  { value: "6", label: "Semestrielle" },
  { value: "12", label: "Annuelle" },
  { value: "24", label: "Tous les 2 ans" },
]

export const intervalLabel = (months: number) =>
  INTERVALS.find((i) => Number(i.value) === months)?.label ?? `Tous les ${months} mois`

export const formatDay = (iso: string) => format(parseISO(iso), "d MMM yyyy", { locale: fr })


export function ProvisionCard({ provision: p, onEdit, onDelete, onToggle }: { provision: Provision; onEdit: () => void; onDelete: () => void; onToggle: () => void }) {
  const constituted = p.funded ?? p.target_now
  const progress = p.amount > 0 ? Math.min(100, (constituted / p.amount) * 100) : 0
  const expected = p.amount > 0 ? Math.min(100, (p.target_now / p.amount) * 100) : 0
  const paidMore = p.last_payment && p.last_payment.amount > p.amount * 1.05

  return (
    <Card className={`rounded-2xl shadow-sm ${p.active ? "" : "opacity-60"}`}>
      <CardContent className="space-y-3 p-4 md:p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-900">{p.name}</p>
            <p className="text-xs text-slate-500">
              {formatCurrency(p.amount)} · {intervalLabel(p.interval_months).toLowerCase()}
              {p.category_name ? ` · ${p.category_name}` : ""}
            </p>
          </div>
          <StatusBadge status={p.status} />
        </div>

        <div>
          <div className="relative h-2 overflow-hidden rounded-full bg-slate-100">
            <div className={`h-full rounded-full ${p.status === "behind" ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${progress}%` }} />
            {p.funded !== null && (
              <div className="absolute top-0 h-full w-0.5 bg-slate-400" style={{ left: `${expected}%` }} title="Ce qui devrait être de côté aujourd'hui" />
            )}
          </div>
          <div className="mt-1 flex justify-between text-xs text-slate-500">
            <span>
              {p.funded !== null ? `${formatCurrency(p.funded)} de côté` : `${formatCurrency(p.target_now)} théoriques`}
            </span>
            <span>échéance le {formatDay(p.next_due)}</span>
          </div>
        </div>

        <div className="rounded-xl bg-slate-50 p-3 text-sm">
          <span className="font-semibold text-slate-900">{formatCurrency(p.monthly_needed)} / mois</span>
          <span className="text-slate-500"> pendant {p.months_left} mois</span>
          {p.status === "behind" && p.monthly_needed > p.monthly_amount + 0.5 && (
            <p className="mt-1 text-xs text-amber-700">Rythme normal : {formatCurrency(p.monthly_amount)} / mois</p>
          )}
        </div>

        {p.last_payment && (
          <p className={`text-xs ${paidMore ? "text-amber-700" : "text-slate-500"}`}>
            Dernier paiement : {formatCurrency(p.last_payment.amount)} le {formatDay(p.last_payment.date)}
            {paidMore && " — plus que prévu, pensez à ajuster le montant"}
          </p>
        )}

        <div className="flex items-center justify-end gap-1">
          <Button variant="ghost" size="sm" className="h-10 md:h-8" onClick={onToggle}>
            {p.active ? "Mettre en pause" : "Réactiver"}
          </Button>
          <Button variant="ghost" size="icon" className="h-10 w-10 md:h-8 md:w-8" onClick={onEdit} title="Modifier">
            <Pencil className="h-4 w-4 text-slate-500" />
          </Button>
          <Button variant="ghost" size="icon" className="h-10 w-10 md:h-8 md:w-8" onClick={onDelete} title="Supprimer">
            <Trash2 className="h-4 w-4 text-rose-500" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function StatusBadge({ status }: { status: Provision["status"] }) {
  if (status === "on_track")
    return <Badge variant="outline" className="gap-1 border-none bg-emerald-50 text-emerald-700"><CheckCircle2 className="h-3 w-3" />À jour</Badge>
  if (status === "behind")
    return <Badge variant="outline" className="gap-1 border-none bg-amber-50 text-amber-700"><AlertTriangle className="h-3 w-3" />En retard</Badge>
  if (status === "inactive") return <Badge variant="outline" className="border-none bg-slate-100 text-slate-500">En pause</Badge>
  return <Badge variant="outline" className="border-none bg-slate-100 text-slate-500">Théorique</Badge>
}
