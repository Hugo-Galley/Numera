import { useEffect, useState } from "react"
import { format } from "date-fns"
import { fr } from "date-fns/locale"
import { ArrowRightLeft, Ban, Link as LinkIcon, PlusCircle } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { AccountLite, TransferCandidate } from "@/types/transfers"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: { id: number; account_id: number; type: string; merchant: string; amount: number; currency: string; date: string } | null
  accounts: AccountLite[]
  onDone: () => void
}

/** Liaison manuelle d'une ligne à un virement interne (cas asynchrones, historique, contrepartie manquante). */
export function TransferLinkDialog({ open, onOpenChange, transaction, accounts, onDone }: Props) {
  const [candidates, setCandidates] = useState<TransferCandidate[]>([])
  const [loading, setLoading] = useState(false)
  const [filterAccount, setFilterAccount] = useState("all")
  const [counterpartAccount, setCounterpartAccount] = useState("")

  const accountName = (id: number) => accounts.find((a) => a.id === id)?.name ?? "Compte inconnu"
  const otherAccounts = accounts.filter((a) => a.id !== transaction?.account_id)

  useEffect(() => {
    if (!open || !transaction) return
    setFilterAccount("all")
    setCounterpartAccount("")
  }, [open, transaction?.id])

  useEffect(() => {
    if (!open || !transaction) return
    let cancelled = false
    setLoading(true)
    const params = new URLSearchParams({ days: "15", amount_tolerance_pct: "5" })
    if (filterAccount !== "all") params.set("account_id", filterAccount)
    api
      .get<TransferCandidate[]>(`/transactions/${transaction.id}/transfer-candidates?${params}`)
      .then((rows) => !cancelled && setCandidates(rows))
      .catch(() => !cancelled && toast.error("Erreur lors de la recherche de candidates"))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [open, transaction?.id, filterAccount])

  if (!transaction) return null
  const isSortie = transaction.type === "Sortie"

  async function link(c: TransferCandidate) {
    try {
      await api.post(`/transactions/${c.sortie_id}/link/${c.other_id}?type=${c.type}`, {})
      toast.success("Virement lié")
      onOpenChange(false)
      onDone()
    } catch {
      toast.error("Échec de la liaison")
    }
  }

  async function createCounterpart() {
    if (!counterpartAccount || !transaction) return
    try {
      await api.post(`/transactions/${transaction.id}/transfer-counterpart`, { account_id: Number(counterpartAccount) })
      toast.success("Contrepartie créée et liée")
      onOpenChange(false)
      onDone()
    } catch {
      toast.error("Impossible de créer la contrepartie")
    }
  }

  async function notATransfer() {
    if (!transaction) return
    try {
      await api.post(`/transactions/${transaction.id}/ignore`, {})
      toast.success("Cette ligne ne sera plus proposée comme virement")
      onOpenChange(false)
      onDone()
    } catch {
      toast.error("Échec de l'action")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowRightLeft className="h-5 w-5 text-indigo-500" />
            Virement interne
          </DialogTitle>
          <DialogDescription>
            {transaction.merchant} · {format(new Date(transaction.date), "dd MMMM yyyy", { locale: fr })} ·{" "}
            <span className="amount-blur">{formatCurrency(transaction.amount, transaction.currency)}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-slate-500">
            {isSortie ? "Entrées" : "Sorties"} proches (±15 jours, ±5 % du montant) sur vos autres comptes.
          </p>
          <Select value={filterAccount} onValueChange={setFilterAccount}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les comptes</SelectItem>
              {otherAccounts.map((a) => (
                <SelectItem key={a.id} value={a.id.toString()}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="max-h-72 space-y-2 overflow-y-auto">
          {loading && <Skeleton className="h-14 w-full" />}
          {!loading && candidates.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-sm italic text-slate-400">
              Aucune candidate. {isSortie && "Vous pouvez créer la contrepartie ci-dessous."}
            </div>
          )}
          {candidates.map((c) => (
            <div key={`${c.type}-${c.other_id}`} className="flex items-center justify-between rounded-xl border border-slate-100 p-3 hover:border-indigo-200">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-slate-900">{c.label || "—"}</p>
                <p className="text-xs text-slate-500">
                  {accountName(c.account_id)} · {format(new Date(c.date), "dd/MM/yyyy")}
                  {c.day_gap > 0 && <span className="ml-1 text-slate-400">({c.day_gap} j d'écart)</span>}
                  {c.amount_gap_pct > 0.001 && <span className="ml-1 text-amber-600">({c.amount_gap_pct.toFixed(1)} % d'écart)</span>}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-bold text-slate-700 amount-blur">{formatCurrency(c.amount, c.currency)}</span>
                <Button size="sm" className="gap-1 bg-indigo-600 hover:bg-indigo-700" onClick={() => link(c)}>
                  <LinkIcon className="h-3.5 w-3.5" />
                  Lier
                </Button>
              </div>
            </div>
          ))}
        </div>

        {isSortie && (
          <div className="flex items-end gap-2 rounded-xl bg-slate-50 p-3">
            <div className="flex-1">
              <p className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500">Créer la contrepartie sur</p>
              <Select value={counterpartAccount} onValueChange={setCounterpartAccount}>
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un compte" />
                </SelectTrigger>
                <SelectContent>
                  {otherAccounts.map((a) => (
                    <SelectItem key={a.id} value={a.id.toString()}>
                      {a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button variant="outline" className="gap-1" disabled={!counterpartAccount} onClick={createCounterpart}>
              <PlusCircle className="h-4 w-4" />
              Créer et lier
            </Button>
          </div>
        )}

        <div className="flex justify-end">
          <Button variant="ghost" size="sm" className="gap-1 text-slate-500" onClick={notATransfer}>
            <Ban className="h-4 w-4" />
            Ce n'est pas un virement
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
