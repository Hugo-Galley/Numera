import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { format } from "date-fns"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ApiError } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { Claim, ClaimCandidate } from "@/types/reimbursements"
import { getReimbursementsClaimsCandidates, postReimbursementsClaimsAllocations } from "@/lib/api/reimbursements"

interface Props {
  claim: Claim | null
  accountName: (id: number) => string
  onOpenChange: (open: boolean) => void
  onDone: () => void
}

export function ClaimCandidatesDialog({ claim, accountName, onOpenChange, onDone }: Props) {
  const { t } = useTranslation("reimbursements")
  const [candidates, setCandidates] = useState<ClaimCandidate[] | null>(null)

  useEffect(() => {
    if (!claim) return
    setCandidates(null)
    getReimbursementsClaimsCandidates<ClaimCandidate[]>(claim.id)
      .then(setCandidates)
      .catch(() => toast.error(t("claimCandidatesDialog.erreurLorsDeLaRecherche")))
  }, [claim, t])

  async function link(c: ClaimCandidate) {
    if (!claim) return
    try {
      await postReimbursementsClaimsAllocations(claim.id, { entree_id: c.id })
      toast.success(t("claimCandidatesDialog.remboursementLie"))
      onDone()
    } catch (e) {
      toast.error(e instanceof ApiError && e.message ? e.message : t("claimCandidatesDialog.echecDeLaLiaison"))
    }
  }

  return (
    <Dialog open={claim !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("claimCandidatesDialog.lierUnRemboursement")}</DialogTitle>
          <DialogDescription>
            {i18n.t("misc.remainingLine", { ns: "reimbursements", debtor: claim?.debtor ?? "", amount: claim ? formatCurrency(claim.remaining, claim.currency) : "", label: claim?.expense.label ?? "" })}
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[60dvh] md:max-h-96 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-100">
          {candidates === null && <p className="p-6 text-center text-sm text-slate-400">{t("claimCandidatesDialog.recherche")}</p>}
          {candidates?.map((c) => (
            <div key={c.id} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 break-words font-medium text-slate-900">
                  {c.label}
                  {c.debtor_match && <Badge variant="outline" className="border-emerald-100 bg-emerald-50 px-1 py-0 text-[10px] text-emerald-700">{t("claimCandidatesDialog.debiteurReconnu")}</Badge>}
                </p>
                <p className="text-xs text-slate-500">
                  {i18n.t("misc.availableLine", { ns: "reimbursements", date: format(new Date(c.date), "dd/MM/yyyy"), account: accountName(c.account_id), amount: formatCurrency(c.available, claim?.currency) })}
                </p>
              </div>
              <Button size="sm" className="h-10 w-full sm:h-9 sm:w-auto" onClick={() => link(c)}>{t("claimCandidatesDialog.lier")}</Button>
            </div>
          ))}
          {candidates?.length === 0 && (
            <p className="p-6 text-center text-sm italic text-slate-400">{t("claimCandidatesDialog.aucuneEntreeDisponibleEntre7")}</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
