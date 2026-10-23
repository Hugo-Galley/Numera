import { useCallback, useEffect, useState } from "react"
import { HandCoins, Link, Pencil, Trash2, X } from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"

import { ClaimCandidatesDialog } from "@/components/reimbursements/ClaimCandidatesDialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api, ApiError } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { Claim, ReimbursementSummary } from "@/types/reimbursements"
import type { AccountLite } from "@/types/transfers"
import { useConfirm } from "@/providers/ConfirmProvider"

export default function Reimbursements() {
  const confirm = useConfirm()
  const [status, setStatus] = useState<"open" | "settled">("open")
  const [debtor, setDebtor] = useState<string | null>(null)
  const [claims, setClaims] = useState<Claim[]>([])
  const [summary, setSummary] = useState<ReimbursementSummary | null>(null)
  const [accounts, setAccounts] = useState<AccountLite[]>([])
  const [loading, setLoading] = useState(true)
  const [linking, setLinking] = useState<Claim | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ status })
      if (debtor) params.set("debtor", debtor)
      const [c, s, a] = await Promise.all([
        api.get<Claim[]>(`/reimbursements/claims?${params}`),
        api.get<ReimbursementSummary>("/reimbursements/summary"),
        api.get<AccountLite[]>("/accounts"),
      ])
      setClaims(c)
      setSummary(s)
      setAccounts(a)
    } catch {
      toast.error("Erreur lors du chargement des remboursements")
    } finally {
      setLoading(false)
    }
  }, [status, debtor])

  useEffect(() => {
    load()
  }, [load])

  const accountName = (id: number) => accounts.find((a) => a.id === id)?.name ?? "Compte inconnu"

  async function editExpected(claim: Claim) {
    const value = prompt(`Montant attendu de ${claim.debtor} (déjà reçu : ${claim.received})`, String(claim.expected_amount))
    if (value === null) return
    const amount = parseFloat(value.replace(",", "."))
    if (!(amount > 0)) {
      toast.error("Montant invalide")
      return
    }
    try {
      await api.patch(`/reimbursements/claims/${claim.id}`, { expected_amount: amount })
      toast.success("Créance modifiée")
      load()
    } catch (e) {
      toast.error(e instanceof ApiError && e.message ? e.message : "Échec de la modification")
    }
  }

  async function remove(claim: Claim) {
    if (!(await confirm(`Supprimer la créance de ${claim.debtor} ? La dépense redevient entièrement à votre charge.`))) return
    try {
      await api.delete(`/reimbursements/claims/${claim.id}`)
      toast.success("Créance supprimée")
      load()
    } catch {
      toast.error("Échec de la suppression")
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl md:text-3xl font-bold tracking-tight">
          <HandCoins className="h-7 w-7 text-emerald-600" />
          Remboursements
        </h1>
        <p className="text-slate-500">
          Dépenses avancées pour d'autres et ce qu'on vous doit encore. Les remboursements liés sont déduits de vos dépenses, sur le mois de la dépense.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:gap-4 lg:grid-cols-4">
        <Card className="col-span-2 border-slate-100 shadow-sm lg:col-span-1">
          <CardContent className="p-4">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">On me doit</p>
            <p className="mt-1 text-2xl font-black text-emerald-600 amount-blur">{formatCurrency(summary?.total_due ?? 0)}</p>
          </CardContent>
        </Card>
        {summary?.debtors.map((d) => (
          <button
            key={d.debtor}
            type="button"
            onClick={() => setDebtor(debtor === d.debtor ? null : d.debtor)}
            className={`min-h-11 min-w-0 rounded-xl border p-3 text-left shadow-sm transition-colors md:p-4 ${
              debtor === d.debtor
                ? "border-emerald-300 bg-emerald-50 dark:bg-emerald-950"
                : "border-slate-100 bg-white hover:border-emerald-200 dark:bg-slate-900"
            }`}
          >
            <p className="break-words font-bold text-slate-900 dark:text-slate-100 md:truncate">{d.debtor}</p>
            <p className="text-sm text-slate-500">
              <span className="amount-blur font-semibold">{formatCurrency(d.due)}</span> · {d.claims} créance{d.claims > 1 ? "s" : ""}
            </p>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Tabs className="max-sm:w-full" value={status} onValueChange={(v) => setStatus(v as "open" | "settled")}>
          <TabsList className="max-sm:grid max-sm:w-full max-sm:grid-cols-2 max-sm:h-11">
            <TabsTrigger value="open">À recevoir</TabsTrigger>
            <TabsTrigger value="settled">Soldées</TabsTrigger>
          </TabsList>
        </Tabs>
        {debtor && (
          <Button variant="outline" size="sm" className="h-10 gap-2 md:h-9" onClick={() => setDebtor(null)}>
            {debtor}
            <X className="h-3.5 w-3.5" />
            <span className="sr-only">Retirer le filtre</span>
          </Button>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
        </div>
      ) : claims.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 md:p-12 text-center text-sm text-slate-400 dark:bg-slate-900">
          <HandCoins className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          {status === "open"
            ? "Personne ne vous doit rien. Déclarez une créance depuis une dépense (icône « On me doit » dans le détail d'un compte)."
            : "Aucune créance soldée."}
        </div>
      ) : (
        <div className="grid gap-3">
          {claims.map((c) => {
            const pct = c.expected_amount > 0 ? Math.min(100, (c.received / c.expected_amount) * 100) : 0
            return (
              <Card key={c.id} className="border-slate-100 shadow-sm">
                <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="font-bold text-slate-900 dark:text-slate-100">{c.debtor}</p>
                    <p className="break-words text-xs text-slate-500 md:truncate">
                      {format(new Date(c.expense.date), "dd/MM/yyyy")} · {c.expense.label} · {accountName(c.expense.account_id)} ·{" "}
                      <span className="amount-blur">{formatCurrency(c.expense.amount, c.currency)}</span>
                    </p>
                    <div className="h-1.5 w-full max-w-sm overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: `${pct}%` }} />
                    </div>
                    <p className="text-xs text-slate-500">
                      <span className="amount-blur">{formatCurrency(c.received, c.currency)}</span> reçu sur{" "}
                      <span className="amount-blur">{formatCurrency(c.expected_amount, c.currency)}</span>
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 md:gap-3">
                    <span className="order-first w-full whitespace-nowrap md:w-auto text-left text-lg font-black tabular-nums text-slate-900 dark:text-slate-100 amount-blur md:order-none md:text-right">{formatCurrency(c.remaining, c.currency)}</span>
                    {c.remaining > 0 && (
                      <Button size="sm" className="h-10 flex-1 gap-2 md:h-9 md:flex-none" onClick={() => setLinking(c)}>
                        <Link className="h-4 w-4" />
                        Lier un remboursement
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" className="h-10 w-10 p-0 text-slate-400 hover:text-indigo-600 md:h-8 md:w-8" onClick={() => editExpected(c)} aria-label="Modifier le montant attendu">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-10 w-10 p-0 text-slate-400 hover:text-red-600 md:h-8 md:w-8" onClick={() => remove(c)} aria-label="Supprimer la créance">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <ClaimCandidatesDialog
        claim={linking}
        accountName={accountName}
        onOpenChange={(o) => !o && setLinking(null)}
        onDone={() => {
          setLinking(null)
          load()
        }}
      />
    </div>
  )
}
