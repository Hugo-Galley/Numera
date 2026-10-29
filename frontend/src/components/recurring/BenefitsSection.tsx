import { useCallback, useEffect, useState } from "react"
import { format, parseISO } from "date-fns"
import { fr } from "date-fns/locale"
import { AlertTriangle, CalendarCheck, CheckCircle2, Clock, HandCoins, Pencil, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorState } from "@/components/layout/ErrorState"
import { api } from "@/lib/api"
import { errorMessage, formatCurrency } from "@/lib/utils"
import { useConfirm } from "@/providers/ConfirmProvider"
import { BenefitDialog, type AccountOption } from "./BenefitDialog"

interface BenefitPayment {
  transaction_id: number
  date: string
  amount: number
  merchant: string
}

export interface Benefit {
  id: number
  name: string
  organization: string
  amount: number
  payment_day: number
  match_pattern: string
  account_id: number | null
  start_date: string | null
  declaration_interval_months: number | null
  next_declaration_date: string | null
  note: string | null
  active: boolean
  account_name: string | null
  status: "received" | "pending" | "late" | "inactive"
  expected_date: string
  next_payment_date: string
  last_payment: BenefitPayment | null
  amount_changed: boolean
  received_this_year: number
  payments: BenefitPayment[]
  declaration_days_left: number | null
}

interface BenefitSummary {
  monthly_expected_total: number
  received_this_year: number
  received_last_12_months: number
  late_count: number
}

const formatDay = (iso: string) => format(parseISO(iso), "d MMM yyyy", { locale: fr })

export function BenefitsSection() {
  const confirm = useConfirm()
  const [benefits, setBenefits] = useState<Benefit[]>([])
  const [summary, setSummary] = useState<BenefitSummary | null>(null)
  const [accounts, setAccounts] = useState<AccountOption[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Benefit | null>(null)

  const load = useCallback(async () => {
    try {
      const [list, sum] = await Promise.all([api.get<Benefit[]>("/benefits"), api.get<BenefitSummary>("/benefits/summary")])
      setBenefits(list)
      setSummary(sum)
      setFailed(false)
    } catch {
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    api.get<(AccountOption & { active?: boolean; type?: string })[]>("/accounts")
      .then((accs) => setAccounts(accs.filter((a) => a.active !== false && a.type !== "investissement")))
      .catch(() => undefined)
  }, [load])

  const openDialog = (benefit: Benefit | null) => {
    setEditing(benefit)
    setDialogOpen(true)
  }

  const mutate = async (request: Promise<unknown>, success: string) => {
    try {
      await request
      toast.success(success)
      load()
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors de la mise à jour"))
    }
  }

  const remove = async (b: Benefit) => {
    if (!(await confirm(`Supprimer l'aide « ${b.name} » ? Les versements reçus restent dans vos transactions.`))) return
    mutate(api.delete(`/benefits/${b.id}`), "Aide supprimée")
  }

  const actions = {
    edit: openDialog,
    remove,
    declared: (b: Benefit) => mutate(api.post(`/benefits/${b.id}/declared`, {}), "Déclaration notée, prochaine échéance avancée"),
    adoptAmount: (b: Benefit) => b.last_payment && mutate(api.patch(`/benefits/${b.id}`, { amount: b.last_payment.amount }), "Montant mis à jour"),
    toggle: (b: Benefit) => mutate(api.patch(`/benefits/${b.id}`, { active: !b.active }), b.active ? "Aide mise en pause" : "Aide réactivée"),
  }

  return (
    <section className="space-y-4 md:space-y-6">
      <div className="flex flex-col justify-between gap-3 border-b pb-3 sm:flex-row sm:items-center md:pb-2">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <HandCoins className="h-5 w-5 text-slate-400" />
          <h2 className="text-xl font-bold text-slate-900">Aides perçues</h2>
          {summary && summary.monthly_expected_total > 0 && (
            <span className="text-sm text-slate-500">
              · {formatCurrency(summary.monthly_expected_total)} / mois · {formatCurrency(summary.received_this_year)} reçus en {new Date().getFullYear()}
            </span>
          )}
        </div>
        <Button className="h-11 w-full rounded-xl shadow-sm sm:h-10 sm:w-auto" onClick={() => openDialog(null)}>
          <Plus className="mr-2 h-4 w-4" />
          Nouvelle aide
        </Button>
      </div>

      {failed ? (
        <ErrorState message="Les aides n'ont pas pu être chargées." onRetry={load} />
      ) : loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1].map((i) => <Skeleton key={i} className="h-48 rounded-2xl" />)}
        </div>
      ) : benefits.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <HandCoins className="h-10 w-10 text-slate-300" />
            <p className="max-w-md text-sm text-slate-500">
              Prime d'activité, APL… Déclarez vos aides pour vérifier chaque mois qu'elles sont bien arrivées et
              recevoir un rappel avant chaque déclaration trimestrielle.
            </p>
            <Button variant="outline" onClick={() => openDialog(null)}>
              <Plus className="mr-2 h-4 w-4" />
              Ajouter une aide
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {benefits.map((b) => <BenefitCard key={b.id} benefit={b} actions={actions} />)}
        </div>
      )}

      <BenefitDialog open={dialogOpen} editing={editing} accounts={accounts} onOpenChange={setDialogOpen} onSaved={load} />
    </section>
  )
}

interface CardActions {
  edit: (b: Benefit) => void
  remove: (b: Benefit) => void
  declared: (b: Benefit) => void
  adoptAmount: (b: Benefit) => void
  toggle: (b: Benefit) => void
}

function BenefitCard({ benefit: b, actions }: { benefit: Benefit; actions: CardActions }) {
  return (
    <Card className={`rounded-2xl shadow-sm ${b.active ? "" : "opacity-60"}`}>
      <CardContent className="space-y-3 p-4 md:p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-900">{b.name}</p>
            <p className="text-xs text-slate-500">
              {b.organization} · {formatCurrency(b.amount)} / mois · vers le {b.payment_day}
              {b.account_name ? ` · ${b.account_name}` : ""}
            </p>
          </div>
          <StatusBadge status={b.status} />
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Dernier versement</p>
            <p className="font-semibold text-slate-900">{b.last_payment ? formatCurrency(b.last_payment.amount) : "Aucun"}</p>
            {b.last_payment && <p className="text-xs text-slate-500">le {formatDay(b.last_payment.date)}</p>}
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Reçu en {new Date().getFullYear()}</p>
            <p className="font-semibold text-slate-900">{formatCurrency(b.received_this_year)}</p>
            <p className="text-xs text-slate-500">prochain le {formatDay(b.next_payment_date)}</p>
          </div>
        </div>

        {b.amount_changed && b.last_payment && b.active && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
            <span>Montant reçu différent de celui attendu ({formatCurrency(b.amount)}).</span>
            <Button size="sm" variant="outline" className="h-9 bg-white md:h-7" onClick={() => actions.adoptAmount(b)}>
              Passer à {formatCurrency(b.last_payment.amount)}
            </Button>
          </div>
        )}

        {b.next_declaration_date && <DeclarationRow benefit={b} onDeclared={() => actions.declared(b)} />}

        {b.payments.length > 1 && (
          <div className="flex flex-wrap gap-1.5" title="Derniers versements">
            {b.payments.slice(0, 6).reverse().map((p) => (
              <span key={p.transaction_id} className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] tabular-nums text-slate-600">
                {format(parseISO(p.date), "MMM", { locale: fr })} {formatCurrency(p.amount)}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center justify-end gap-1">
          <Button variant="ghost" size="sm" className="h-10 md:h-8" onClick={() => actions.toggle(b)}>
            {b.active ? "Mettre en pause" : "Réactiver"}
          </Button>
          <Button variant="ghost" size="icon" className="h-10 w-10 md:h-8 md:w-8" onClick={() => actions.edit(b)} title="Modifier">
            <Pencil className="h-4 w-4 text-slate-500" />
          </Button>
          <Button variant="ghost" size="icon" className="h-10 w-10 md:h-8 md:w-8" onClick={() => actions.remove(b)} title="Supprimer">
            <Trash2 className="h-4 w-4 text-rose-500" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function DeclarationRow({ benefit: b, onDeclared }: { benefit: Benefit; onDeclared: () => void }) {
  const days = b.declaration_days_left ?? 0
  const urgent = days <= 7
  const when = days < 0 ? `en retard de ${-days} j` : days === 0 ? "aujourd'hui" : `dans ${days} j`
  return (
    <div className={`flex flex-wrap items-center justify-between gap-2 rounded-xl p-3 text-sm ${urgent ? "border border-rose-200 bg-rose-50 text-rose-800" : "bg-slate-50 text-slate-600"}`}>
      <span className="flex items-center gap-2">
        <CalendarCheck className="h-4 w-4 shrink-0" />
        Déclaration le {formatDay(b.next_declaration_date!)} ({when})
      </span>
      <Button size="sm" variant="outline" className="h-9 bg-white md:h-7" onClick={onDeclared}>
        Déclaration faite
      </Button>
    </div>
  )
}

function StatusBadge({ status }: { status: Benefit["status"] }) {
  if (status === "received")
    return <Badge variant="outline" className="gap-1 border-none bg-emerald-50 text-emerald-700"><CheckCircle2 className="h-3 w-3" />Reçue</Badge>
  if (status === "late")
    return <Badge variant="outline" className="gap-1 border-none bg-rose-50 text-rose-700"><AlertTriangle className="h-3 w-3" />Non reçue</Badge>
  if (status === "inactive") return <Badge variant="outline" className="border-none bg-slate-100 text-slate-500">En pause</Badge>
  return <Badge variant="outline" className="gap-1 border-none bg-slate-100 text-slate-600"><Clock className="h-3 w-3" />En attente</Badge>
}
