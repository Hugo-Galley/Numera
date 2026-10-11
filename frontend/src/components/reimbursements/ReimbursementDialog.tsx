import { useCallback, useEffect, useState } from "react"
import { HandCoins, Plus, Trash2, Users } from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api, ApiError } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { Claim, EntryClaims, ReimbursableTransaction } from "@/types/reimbursements"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: ReimbursableTransaction | null
  onDone: () => void
}

const parseAmount = (value: string) => parseFloat(value.replace(",", "."))
const errorMessage = (e: unknown, fallback: string) => (e instanceof ApiError && e.message ? e.message : fallback)

export function ReimbursementDialog({ open, onOpenChange, transaction, onDone }: Props) {
  const [claims, setClaims] = useState<Claim[]>([])
  const [entry, setEntry] = useState<EntryClaims | null>(null)
  const [debtor, setDebtor] = useState("")
  const [expected, setExpected] = useState("")
  const [splitCount, setSplitCount] = useState("2")
  const [allocInputs, setAllocInputs] = useState<Record<number, string>>({})

  const isSortie = transaction?.type === "Sortie"

  const load = useCallback(async () => {
    if (!transaction) return
    try {
      if (transaction.type === "Sortie") {
        const all = await api.get<Claim[]>("/reimbursements/claims?status=all")
        setClaims(all.filter((c) => c.expense.id === transaction.id))
      } else {
        setEntry(await api.get<EntryClaims>(`/reimbursements/entries/${transaction.id}/claims`))
      }
    } catch {
      toast.error("Erreur lors du chargement des remboursements")
    }
  }, [transaction])

  useEffect(() => {
    if (open) {
      setDebtor("")
      setExpected("")
      setAllocInputs({})
      setClaims([])
      setEntry(null)
      load()
    }
  }, [open, load])

  const declared = claims.reduce((sum, c) => sum + c.expected_amount, 0)

  async function addClaim(name: string, amount: number) {
    if (!transaction) return
    await api.post("/reimbursements/claims", { transaction_id: transaction.id, debtor: name, expected_amount: amount })
  }

  async function handleAdd() {
    const amount = parseAmount(expected)
    if (!debtor.trim() || !(amount > 0)) {
      toast.error("Indiquez un débiteur et un montant")
      return
    }
    try {
      await addClaim(debtor.trim(), amount)
      toast.success("Créance ajoutée")
      setDebtor("")
      setExpected("")
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Impossible d'ajouter la créance"))
    }
  }

  async function handleSplit() {
    if (!transaction) return
    const n = parseInt(splitCount)
    if (!(n >= 2)) {
      toast.error("Indiquez au moins 2 personnes (vous compris)")
      return
    }
    // La dépense est partagée entre n personnes dont vous : n − 1 créances d'une part chacune
    const share = Math.floor((transaction.amount / n) * 100) / 100
    try {
      for (let i = 1; i < n; i++) await addClaim(`Personne ${i}`, share)
      toast.success(`${n - 1} créances de ${formatCurrency(share, transaction.currency)} ajoutées : renommez les débiteurs`)
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Impossible de répartir la dépense"))
    }
  }

  async function handleDeleteClaim(claim: Claim) {
    if (!confirm(`Supprimer la créance de ${claim.debtor} ?`)) return
    try {
      await api.delete(`/reimbursements/claims/${claim.id}`)
      toast.success("Créance supprimée")
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Échec de la suppression"))
    }
  }

  async function handleRename(claim: Claim, name: string) {
    if (!name.trim() || name.trim() === claim.debtor) return
    try {
      await api.patch(`/reimbursements/claims/${claim.id}`, { debtor: name.trim() })
      toast.success("Débiteur renommé")
      load()
    } catch (e) {
      toast.error(errorMessage(e, "Échec de la modification"))
    }
  }

  async function handleAllocate(claim: Claim) {
    if (!transaction) return
    const raw = allocInputs[claim.id]
    const amount = raw ? parseAmount(raw) : undefined
    try {
      await api.post(`/reimbursements/claims/${claim.id}/allocations`, { entree_id: transaction.id, ...(amount ? { amount } : {}) })
      toast.success(`Remboursement affecté à ${claim.debtor}`)
      setAllocInputs({ ...allocInputs, [claim.id]: "" })
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Échec de l'affectation"))
    }
  }

  async function handleRemoveAllocation(id: number) {
    try {
      await api.delete(`/reimbursements/allocations/${id}`)
      toast.success("Affectation retirée")
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Échec de l'action"))
    }
  }

  if (!transaction) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HandCoins className="h-5 w-5 text-emerald-600" />
            {isSortie ? "On me doit" : "Affecter un remboursement"}
          </DialogTitle>
          <DialogDescription>
            {transaction.merchant} · {format(new Date(transaction.date), "dd/MM/yyyy")} ·{" "}
            <span className="amount-blur">{formatCurrency(transaction.amount, transaction.currency)}</span>
          </DialogDescription>
        </DialogHeader>

        {isSortie ? (
          <div className="space-y-4">
            <div className="divide-y divide-slate-100 rounded-xl border border-slate-100">
              {claims.map((c) => (
                <div key={c.id} className="space-y-1 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <Input defaultValue={c.debtor} className="h-8 max-w-[12rem]" onBlur={(e) => handleRename(c, e.target.value)} />
                    <span className="text-sm text-slate-600">
                      <span className="amount-blur font-semibold text-emerald-600">{formatCurrency(c.received, c.currency)}</span>
                      {" / "}
                      <span className="amount-blur">{formatCurrency(c.expected_amount, c.currency)}</span>
                    </span>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-slate-400 hover:text-red-600" onClick={() => handleDeleteClaim(c)} aria-label="Supprimer la créance">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  {c.allocations.map((a) => (
                    <p key={a.id} className="text-xs text-slate-500">
                      {a.date ? format(new Date(a.date), "dd/MM/yyyy") : ""} · {a.label} ·{" "}
                      <span className="amount-blur">{formatCurrency(a.amount, c.currency)}</span>
                    </p>
                  ))}
                </div>
              ))}
              {claims.length === 0 && <p className="p-4 text-center text-sm italic text-slate-400">Aucune créance sur cette dépense.</p>}
            </div>
            <p className="text-xs text-slate-500">
              Déclaré : <span className="amount-blur">{formatCurrency(declared, transaction.currency)}</span> sur{" "}
              <span className="amount-blur">{formatCurrency(transaction.amount, transaction.currency)}</span>
            </p>
            <div className="grid grid-cols-1 items-end gap-2 sm:grid-cols-[1fr_8rem_auto]">
              <div className="grid gap-1">
                <Label htmlFor="claim-debtor">Qui me doit</Label>
                <Input id="claim-debtor" value={debtor} onChange={(e) => setDebtor(e.target.value)} placeholder="Denis, Sécu…" />
              </div>
              <div className="grid gap-1">
                <Label htmlFor="claim-amount">Montant</Label>
                <Input id="claim-amount" inputMode="decimal" value={expected} onChange={(e) => setExpected(e.target.value)} />
              </div>
              <Button className="gap-2" onClick={handleAdd}>
                <Plus className="h-4 w-4" />
                Ajouter
              </Button>
            </div>
            {claims.length === 0 && (
              <div className="flex flex-wrap items-end gap-2 rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <div className="grid gap-1">
                  <Label htmlFor="claim-split">Partager à parts égales entre (vous compris)</Label>
                  <Input id="claim-split" inputMode="numeric" className="w-24" value={splitCount} onChange={(e) => setSplitCount(e.target.value)} />
                </div>
                <Button variant="outline" className="gap-2" onClick={handleSplit}>
                  <Users className="h-4 w-4" />
                  Répartir
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Disponible : <span className="amount-blur font-semibold">{formatCurrency(entry?.available ?? 0, transaction.currency)}</span>
            </p>
            {entry?.allocations.map((a) => (
              <div key={a.id} className="flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2 text-sm dark:bg-emerald-950">
                <span>
                  Affecté à {a.debtor} : <span className="amount-blur font-semibold">{formatCurrency(a.amount, transaction.currency)}</span>
                </span>
                <Button variant="ghost" size="sm" onClick={() => handleRemoveAllocation(a.id)}>Retirer</Button>
              </div>
            ))}
            <div className="max-h-72 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-100">
              {entry?.open_claims.map((c) => (
                <div key={c.id} className="flex items-center justify-between gap-3 p-3">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900 dark:text-slate-100">{c.debtor}</p>
                    <p className="truncate text-xs text-slate-500">
                      {format(new Date(c.expense.date), "dd/MM/yyyy")} · {c.expense.label} · reste{" "}
                      <span className="amount-blur">{formatCurrency(c.remaining, c.currency)}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      inputMode="decimal"
                      className="h-8 w-24"
                      placeholder={String(Math.min(c.remaining, entry.available))}
                      value={allocInputs[c.id] ?? ""}
                      onChange={(e) => setAllocInputs({ ...allocInputs, [c.id]: e.target.value })}
                    />
                    <Button size="sm" onClick={() => handleAllocate(c)} disabled={entry.available <= 0}>Affecter</Button>
                  </div>
                </div>
              ))}
              {entry && entry.open_claims.length === 0 && (
                <p className="p-4 text-center text-sm italic text-slate-400">Aucune créance ouverte. Déclarez-la d'abord sur la dépense.</p>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
