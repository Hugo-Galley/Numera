import { useEffect, useState } from "react"
import { format } from "date-fns"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { api, ApiError } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { Claim, ClaimCandidate } from "@/types/reimbursements"

interface Props {
  claim: Claim | null
  accountName: (id: number) => string
  onOpenChange: (open: boolean) => void
  onDone: () => void
}

export function ClaimCandidatesDialog({ claim, accountName, onOpenChange, onDone }: Props) {
  const [candidates, setCandidates] = useState<ClaimCandidate[] | null>(null)

  useEffect(() => {
    if (!claim) return
    setCandidates(null)
    api.get<ClaimCandidate[]>(`/reimbursements/claims/${claim.id}/candidates`)
      .then(setCandidates)
      .catch(() => toast.error("Erreur lors de la recherche des remboursements"))
  }, [claim])

  async function link(c: ClaimCandidate) {
    if (!claim) return
    try {
      await api.post(`/reimbursements/claims/${claim.id}/allocations`, { entree_id: c.id })
      toast.success("Remboursement lié")
      onDone()
    } catch (e) {
      toast.error(e instanceof ApiError && e.message ? e.message : "Échec de la liaison")
    }
  }

  return (
    <Dialog open={claim !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Lier un remboursement</DialogTitle>
          <DialogDescription>
            {claim?.debtor} · reste <span className="amount-blur">{claim ? formatCurrency(claim.remaining, claim.currency) : ""}</span> · {claim?.expense.label}
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-96 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-100">
          {candidates === null && <p className="p-6 text-center text-sm text-slate-400">Recherche…</p>}
          {candidates?.map((c) => (
            <div key={c.id} className="flex items-center justify-between gap-3 p-3">
              <div className="min-w-0">
                <p className="flex items-center gap-2 truncate font-medium text-slate-900 dark:text-slate-100">
                  {c.label}
                  {c.debtor_match && <Badge variant="outline" className="border-emerald-100 bg-emerald-50 px-1 py-0 text-[10px] text-emerald-700">Débiteur reconnu</Badge>}
                </p>
                <p className="text-xs text-slate-500">
                  {format(new Date(c.date), "dd/MM/yyyy")} · {accountName(c.account_id)} · disponible{" "}
                  <span className="amount-blur">{formatCurrency(c.available, claim?.currency)}</span>
                </p>
              </div>
              <Button size="sm" onClick={() => link(c)}>Lier</Button>
            </div>
          ))}
          {candidates?.length === 0 && (
            <p className="p-6 text-center text-sm italic text-slate-400">Aucune entrée disponible entre 7 jours avant et 180 jours après la dépense.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
