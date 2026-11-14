import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { useCallback, useEffect, useState } from "react"
import { HandCoins, Plus, Trash2, Users } from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { Claim, EntryClaims, ReimbursableTransaction } from "@/types/reimbursements"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useSubmit } from "@/hooks/useSubmit"
import { deleteReimbursementsAllocationsById, deleteReimbursementsClaimsById, getReimbursementsClaims, getReimbursementsEntriesClaims, patchReimbursementsClaimsById, postReimbursementsClaims, postReimbursementsClaimsAllocations } from "@/lib/api/reimbursements"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: ReimbursableTransaction | null
  onDone: () => void
}

const parseAmount = (value: string) => parseFloat(value.replace(",", "."))
const errorMessage = (e: unknown, fallback: string) => (e instanceof ApiError && e.message ? e.message : fallback)

export function ReimbursementDialog({ open, onOpenChange, transaction, onDone }: Props) {
  const { t } = useTranslation("reimbursements")
  const confirm = useConfirm()
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
        const all = await getReimbursementsClaims<Claim[]>("?status=all")
        setClaims(all.filter((c) => c.expense.id === transaction.id))
      } else {
        setEntry(await getReimbursementsEntriesClaims<EntryClaims>(transaction.id))
      }
    } catch {
      toast.error(t("reimbursementDialog.erreurLorsDuChargementDes"))
    }
  }, [transaction, t])

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

  // « Ajouter » et « Répartir » partagent un verrou : un double clic ne crée pas deux fois les créances
  const [submit, submitting] = useSubmit((action: () => Promise<void>) => action())

  async function addClaim(name: string, amount: number) {
    if (!transaction) return
    await postReimbursementsClaims({ transaction_id: transaction.id, debtor: name, expected_amount: amount })
  }

  async function handleAdd() {
    const amount = parseAmount(expected)
    if (!debtor.trim() || !(amount > 0)) {
      toast.error(t("reimbursementDialog.indiquezUnDebiteurEtUn"))
      return
    }
    try {
      await addClaim(debtor.trim(), amount)
      toast.success(t("reimbursementDialog.creanceAjoutee"))
      setDebtor("")
      setExpected("")
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, t("reimbursementDialog.impossibleDAjouterLaCreance")))
    }
  }

  async function handleSplit() {
    if (!transaction) return
    const n = parseInt(splitCount)
    if (!(n >= 2)) {
      toast.error(t("reimbursementDialog.indiquezAuMoins2Personnes"))
      return
    }
    // La dépense est partagée entre n personnes dont vous : n − 1 créances d'une part chacune
    const share = Math.floor((transaction.amount / n) * 100) / 100
    try {
      for (let i = 1; i < n; i++) await addClaim(i18n.t("misc.person", { ns: "reimbursements", index: i }), share)
      toast.success(i18n.t("misc.splitDone", { ns: "reimbursements", count: n - 1, amount: formatCurrency(share, transaction.currency) }))
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, t("reimbursementDialog.impossibleDeRepartirLaDepense")))
    }
  }

  async function handleDeleteClaim(claim: Claim) {
    if (!(await confirm(i18n.t("misc.deleteClaimConfirm", { ns: "reimbursements", debtor: claim.debtor })))) return
    try {
      await deleteReimbursementsClaimsById(claim.id)
      toast.success(t("reimbursementDialog.creanceSupprimee"))
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, t("reimbursementDialog.echecDeLaSuppression")))
    }
  }

  async function handleRename(claim: Claim, name: string) {
    if (!name.trim() || name.trim() === claim.debtor) return
    try {
      await patchReimbursementsClaimsById(claim.id, { debtor: name.trim() })
      toast.success(t("reimbursementDialog.debiteurRenomme"))
      load()
    } catch (e) {
      toast.error(errorMessage(e, t("reimbursementDialog.echecDeLaModification")))
    }
  }

  async function handleAllocate(claim: Claim) {
    if (!transaction) return
    const raw = allocInputs[claim.id]
    const amount = raw ? parseAmount(raw) : undefined
    try {
      await postReimbursementsClaimsAllocations(claim.id, { entree_id: transaction.id, ...(amount ? { amount } : {}) })
      toast.success(i18n.t("misc.allocated", { ns: "reimbursements", debtor: claim.debtor }))
      setAllocInputs({ ...allocInputs, [claim.id]: "" })
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, t("reimbursementDialog.echecDeLAffectation")))
    }
  }

  async function handleRemoveAllocation(id: number) {
    try {
      await deleteReimbursementsAllocationsById(id)
      toast.success(t("reimbursementDialog.affectationRetiree"))
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, t("reimbursementDialog.echecDeLAction")))
    }
  }

  if (!transaction) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HandCoins className="h-5 w-5 text-emerald-600" />
            {isSortie ? t("reimbursementDialog.onMeDoit") : t("reimbursementDialog.affecterUnRemboursement")}
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
                  <div className="flex flex-wrap items-center justify-between gap-2 sm:gap-3">
                    <Input defaultValue={c.debtor} className="h-10 min-w-0 flex-1 text-base sm:h-8 sm:max-w-48 sm:flex-none sm:text-sm" onBlur={(e) => handleRename(c, e.target.value)} />
                    <span className="whitespace-nowrap text-sm text-slate-600">
                      <span className="amount-blur font-semibold text-emerald-600">{formatCurrency(c.received, c.currency)}</span>
                      {" / "}
                      <span className="amount-blur">{formatCurrency(c.expected_amount, c.currency)}</span>
                    </span>
                    <Button variant="ghost" size="sm" className="h-10 w-10 p-0 text-slate-400 hover:text-red-600 sm:h-8 sm:w-8" onClick={() => handleDeleteClaim(c)} aria-label={t("reimbursementDialog.supprimerLaCreance")}>
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
              {claims.length === 0 && <p className="p-4 text-center text-sm italic text-slate-400">{t("reimbursementDialog.aucuneCreanceSurCetteDepense")}</p>}
            </div>
            <p className="text-xs text-slate-500">
              {t("reimbursementDialog.declare")} <span className="amount-blur">{formatCurrency(declared, transaction.currency)}</span> sur{" "}
              <span className="amount-blur">{formatCurrency(transaction.amount, transaction.currency)}</span>
            </p>
            <div className="grid grid-cols-1 items-end gap-2 sm:grid-cols-[1fr_8rem_auto]">
              <div className="grid gap-1">
                <Label htmlFor="claim-debtor">{t("reimbursementDialog.quiMeDoit")}</Label>
                <Input id="claim-debtor" className="h-10 text-base sm:h-9 sm:text-sm" value={debtor} onChange={(e) => setDebtor(e.target.value)} placeholder={t("reimbursementDialog.denisSecu")} />
              </div>
              <div className="grid gap-1">
                <Label htmlFor="claim-amount">{t("reimbursementDialog.montant")}</Label>
                <Input id="claim-amount" className="h-10 text-base sm:h-9 sm:text-sm" inputMode="decimal" value={expected} onChange={(e) => setExpected(e.target.value)} />
              </div>
              <Button className="h-10 gap-2 sm:h-9" onClick={() => submit(handleAdd)} disabled={submitting}>
                <Plus className="h-4 w-4" />
                {t("reimbursementDialog.ajouter")}
              </Button>
            </div>
            {claims.length === 0 && (
              <div className="flex flex-wrap items-end gap-2 rounded-xl bg-slate-50 p-3">
                <div className="grid gap-1">
                  <Label htmlFor="claim-split">{t("reimbursementDialog.partagerAPartsEgalesEntre")}</Label>
                  <Input id="claim-split" inputMode="numeric" className="h-10 w-24 text-base sm:h-9 sm:text-sm" value={splitCount} onChange={(e) => setSplitCount(e.target.value)} />
                </div>
                <Button variant="outline" className="h-10 gap-2 sm:h-9" onClick={() => submit(handleSplit)} disabled={submitting}>
                  <Users className="h-4 w-4" />
                  {t("reimbursementDialog.repartir")}
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              {t("reimbursementDialog.disponible")} <span className="amount-blur font-semibold">{formatCurrency(entry?.available ?? 0, transaction.currency)}</span>
            </p>
            {entry?.allocations.map((a) => (
              <div key={a.id} className="flex items-center justify-between gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm">
                <span>
                  Affecté à {a.debtor} : <span className="amount-blur font-semibold">{formatCurrency(a.amount, transaction.currency)}</span>
                </span>
                <Button variant="ghost" size="sm" className="h-10 sm:h-9" onClick={() => handleRemoveAllocation(a.id)}>{t("reimbursementDialog.retirer")}</Button>
              </div>
            ))}
            <div className="max-h-[50dvh] sm:max-h-72 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-100">
              {entry?.open_claims.map((c) => (
                <div key={c.id} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{c.debtor}</p>
                    <p className="wrap-break-word text-xs text-slate-500 sm:truncate">
                      {i18n.t("misc.expenseRemaining", { ns: "reimbursements", date: format(new Date(c.expense.date), "dd/MM/yyyy"), label: c.expense.label, amount: formatCurrency(c.remaining, c.currency) })}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      inputMode="decimal"
                      className="h-10 flex-1 text-base sm:h-8 sm:w-24 sm:flex-none sm:text-sm"
                      placeholder={String(Math.min(c.remaining, entry.available))}
                      value={allocInputs[c.id] ?? ""}
                      onChange={(e) => setAllocInputs({ ...allocInputs, [c.id]: e.target.value })}
                    />
                    <Button size="sm" className="h-10 sm:h-9" onClick={() => handleAllocate(c)} disabled={entry.available <= 0}>{t("reimbursementDialog.affecter")}</Button>
                  </div>
                </div>
              ))}
              {entry && entry.open_claims.length === 0 && (
                <p className="p-4 text-center text-sm italic text-slate-400">{t("reimbursementDialog.aucuneCreanceOuverteDeclarezLa")}</p>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
