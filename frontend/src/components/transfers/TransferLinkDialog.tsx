import { useTranslation } from "react-i18next"
import { dateLocale } from "@/i18n/locale"
import { useEffect, useState } from "react"
import { format } from "date-fns"
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
import { formatCurrency, formatRate } from "@/lib/utils"
import type { AccountLite, TransferCandidate } from "@/types/transfers"
import { getTransactionsTransferCandidates, postTransactionsIgnore, postTransactionsLinkById, postTransactionsTransferCounterpart } from "@/lib/api/transactions"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: { id: number; account_id: number; type: string; merchant: string; amount: number; currency: string; date: string } | null
  accounts: AccountLite[]
  onDone: () => void
}

/** Liaison manuelle d'une ligne à un virement interne (cas asynchrones, historique, contrepartie manquante). */
export function TransferLinkDialog({ open, onOpenChange, transaction, accounts, onDone }: Props) {
  const { t } = useTranslation("transactions")
  const [candidates, setCandidates] = useState<TransferCandidate[]>([])
  const [loading, setLoading] = useState(false)
  const [filterAccount, setFilterAccount] = useState("all")
  const [counterpartAccount, setCounterpartAccount] = useState("")

  const accountName = (id: number) => accounts.find((a) => a.id === id)?.name ?? t("transferLinkDialog.unknownAccount")
  const otherAccounts = accounts.filter((a) => a.id !== transaction?.account_id)

  const transactionId = transaction?.id

  useEffect(() => {
    if (!open || transactionId === undefined) return
    setFilterAccount("all")
    setCounterpartAccount("")
  }, [open, transactionId])

  useEffect(() => {
    if (!open || transactionId === undefined) return
    let cancelled = false
    setLoading(true)
    const params = new URLSearchParams({ days: "15", amount_tolerance_pct: "5" })
    if (filterAccount !== "all") params.set("account_id", filterAccount)
    getTransactionsTransferCandidates<TransferCandidate[]>(transactionId, `?${params}`)
      .then((rows) => !cancelled && setCandidates(rows))
      .catch(() => !cancelled && toast.error(t("transferLinkDialog.erreurLorsDeLaRecherche")))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [open, transactionId, filterAccount, t])

  if (!transaction) return null
  const isSortie = transaction.type === "Sortie"

  async function link(c: TransferCandidate) {
    try {
      await postTransactionsLinkById(c.sortie_id, c.other_id, `?type=${c.type}`, {})
      toast.success(t("transferLinkDialog.virementLie"))
      onOpenChange(false)
      onDone()
    } catch {
      toast.error(t("transferLinkDialog.echecDeLaLiaison"))
    }
  }

  async function createCounterpart() {
    if (!counterpartAccount || !transaction) return
    try {
      await postTransactionsTransferCounterpart(transaction.id, { account_id: Number(counterpartAccount) })
      toast.success(t("transferLinkDialog.contrepartieCreeeEtLiee"))
      onOpenChange(false)
      onDone()
    } catch {
      toast.error(t("transferLinkDialog.impossibleDeCreerLaContrepartie"))
    }
  }

  async function notATransfer() {
    if (!transaction) return
    try {
      await postTransactionsIgnore(transaction.id, "", {})
      toast.success(t("transferLinkDialog.cetteLigneNeSeraPlus"))
      onOpenChange(false)
      onDone()
    } catch {
      toast.error(t("transferLinkDialog.echecDeLAction"))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowRightLeft className="h-5 w-5 text-indigo-500" />
            {t("transferLinkDialog.virementInterne")}
          </DialogTitle>
          <DialogDescription>
            {transaction.merchant} · {format(new Date(transaction.date), "dd MMMM yyyy", { locale: dateLocale() })} ·{" "}
            <span className="amount-blur">{formatCurrency(transaction.amount, transaction.currency)}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
          <p className="text-sm text-slate-500">
            {isSortie ? t("transferLinkDialog.entrees") : t("transferLinkDialog.sorties")} proches (±15 jours, ±5 % du montant) sur vos autres comptes.
          </p>
          <Select value={filterAccount} onValueChange={setFilterAccount}>
            <SelectTrigger className="h-11 w-full sm:h-10 sm:w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("transferLinkDialog.tousLesComptes")}</SelectItem>
              {otherAccounts.map((a) => (
                <SelectItem key={a.id} value={a.id.toString()}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="max-h-[40dvh] space-y-2 overflow-y-auto sm:max-h-72">
          {loading && <Skeleton className="h-14 w-full" />}
          {!loading && candidates.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-sm italic text-slate-400">
              {t("transferLinkDialog.noCandidate")} {isSortie && t("transferLinkDialog.createBelow")}
            </div>
          )}
          {candidates.map((c) => (
            <div key={`${c.type}-${c.other_id}`} className="flex flex-col gap-2 rounded-xl border border-slate-100 p-3 hover:border-indigo-200 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-slate-900">{c.label || "—"}</p>
                <p className="text-xs text-slate-500">
                  {accountName(c.account_id)} · {format(new Date(c.date), "dd/MM/yyyy")}
                  {c.day_gap > 0 && <span className="ml-1 text-slate-400">({c.day_gap} j d'écart)</span>}
                  {c.amount_gap_pct > 0.001 && <span className="ml-1 text-amber-600">({formatRate(c.amount_gap_pct, 1)} d'écart)</span>}
                </p>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="whitespace-nowrap font-bold tabular-nums text-slate-700 amount-blur">{formatCurrency(c.amount, c.currency)}</span>
                <Button size="sm" className="h-10 gap-1 bg-indigo-600 hover:bg-indigo-700 sm:h-9" onClick={() => link(c)}>
                  <LinkIcon className="h-3.5 w-3.5" />
                  {t("transferLinkDialog.lier")}
                </Button>
              </div>
            </div>
          ))}
        </div>

        {isSortie && (
          <div className="flex flex-col gap-2 rounded-xl bg-slate-50 p-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <p className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500">{t("transferLinkDialog.creerLaContrepartieSur")}</p>
              <Select value={counterpartAccount} onValueChange={setCounterpartAccount}>
                <SelectTrigger className="h-11 sm:h-10">
                  <SelectValue placeholder={t("transferLinkDialog.choisirUnCompte")} />
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
            <Button variant="outline" className="h-11 gap-1 sm:h-10" disabled={!counterpartAccount} onClick={createCounterpart}>
              <PlusCircle className="h-4 w-4" />
              {t("transferLinkDialog.creerEtLier")}
            </Button>
          </div>
        )}

        <div className="flex justify-end">
          <Button variant="ghost" size="sm" className="h-10 gap-1 text-slate-500" onClick={notATransfer}>
            <Ban className="h-4 w-4" />
            {t("transferLinkDialog.ceNEstPasUn")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
