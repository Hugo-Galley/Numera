import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { dateLocale } from "@/i18n/locale"
import { AlertTriangle, CheckCircle2, Pencil, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { format, parseISO } from "date-fns"
import { formatCurrency } from "@/lib/utils"

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

export const intervals = (): { value: string; label: string }[] => [
  { value: "1", label: i18n.t("provisionCard.mensuelle", { ns: "savings" }) },
  { value: "3", label: i18n.t("provisionCard.trimestrielle", { ns: "savings" }) },
  { value: "6", label: i18n.t("provisionCard.semestrielle", { ns: "savings" }) },
  { value: "12", label: i18n.t("provisionCard.annuelle", { ns: "savings" }) },
  { value: "24", label: i18n.t("provisionCard.tousLes2Ans", { ns: "savings" }) },
]

export const intervalLabel = (months: number) =>
  intervals().find((i) => Number(i.value) === months)?.label ?? i18n.t("provisionCard.everyMonths", { ns: "savings", count: months })

export const formatDay = (iso: string) => format(parseISO(iso), "d MMM yyyy", { locale: dateLocale() })


export function ProvisionCard({ provision: p, onEdit, onDelete, onToggle }: { provision: Provision; onEdit: () => void; onDelete: () => void; onToggle: () => void }) {
  const { t } = useTranslation("savings")
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
              <div className="absolute top-0 h-full w-0.5 bg-slate-400" style={{ left: `${expected}%` }} title={t("provisionCard.ceQuiDevraitEtreDe")} />
            )}
          </div>
          <div className="mt-1 flex justify-between text-xs text-slate-500">
            <span>
              {p.funded !== null ? i18n.t("misc.fundedSet", { ns: "savings", amount: formatCurrency(p.funded) }) : i18n.t("misc.theoretical", { ns: "savings", amount: formatCurrency(p.target_now) })}
            </span>
            <span>{i18n.t("misc.dueOn", { ns: "savings", date: formatDay(p.next_due) })}</span>
          </div>
        </div>

        <div className="rounded-xl bg-slate-50 p-3 text-sm">
          <span className="font-semibold text-slate-900">{i18n.t("misc.perMonth", { ns: "savings", amount: formatCurrency(p.monthly_needed) })}</span>
          <span className="text-slate-500">{i18n.t("misc.forMonths", { ns: "savings", count: p.months_left })}</span>
          {p.status === "behind" && p.monthly_needed > p.monthly_amount + 0.5 && (
            <p className="mt-1 text-xs text-amber-700">{i18n.t("misc.normalPace", { ns: "savings", amount: formatCurrency(p.monthly_amount) })}</p>
          )}
        </div>

        {p.last_payment && (
          <p className={`text-xs ${paidMore ? "text-amber-700" : "text-slate-500"}`}>
            {i18n.t("misc.lastPayment", { ns: "savings", amount: formatCurrency(p.last_payment.amount), date: formatDay(p.last_payment.date) })}
            {paidMore && i18n.t("misc.paidMore", { ns: "savings" })}
          </p>
        )}

        <div className="flex items-center justify-end gap-1">
          <Button variant="ghost" size="sm" className="h-10 md:h-8" onClick={onToggle}>
            {p.active ? t("provisionCard.mettreEnPause") : t("provisionCard.reactiver")}
          </Button>
          <Button variant="ghost" size="icon" className="h-10 w-10 md:h-8 md:w-8" onClick={onEdit} title={t("provisionCard.modifier")}>
            <Pencil className="h-4 w-4 text-slate-500" />
          </Button>
          <Button variant="ghost" size="icon" className="h-10 w-10 md:h-8 md:w-8" onClick={onDelete} title={t("provisionCard.supprimer")}>
            <Trash2 className="h-4 w-4 text-rose-500" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function StatusBadge({ status }: { status: Provision["status"] }) {
  const { t } = useTranslation("savings")
  if (status === "on_track")
    return <Badge variant="outline" className="gap-1 border-none bg-emerald-50 text-emerald-700"><CheckCircle2 className="h-3 w-3" />{t("provisionCard.aJour")}</Badge>
  if (status === "behind")
    return <Badge variant="outline" className="gap-1 border-none bg-amber-50 text-amber-700"><AlertTriangle className="h-3 w-3" />{t("provisionCard.enRetard")}</Badge>
  if (status === "inactive") return <Badge variant="outline" className="border-none bg-slate-100 text-slate-500">{t("provisionCard.enPause")}</Badge>
  return <Badge variant="outline" className="border-none bg-slate-100 text-slate-500">{t("provisionCard.theorique")}</Badge>
}
