/** Étape « Comptes » de la revue de mois : rapprochement au solde du relevé, comptes inchangés, placements. */
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"

import { Card, CardContent } from "@/components/ui/card"
import { appLocale } from "@/i18n/locale"
import { postAccountsVerify } from "@/lib/api/accounts"
import type { MonthReview, ReviewAccount } from "@/types/monthReview"
import { MarketBlock } from "./MarketBlock"
import { ReconcileRow } from "./ReconcileRow"
import { UnchangedBlock } from "./UnchangedBlock"

export interface AccountsStepProps {
  step: MonthReview["accounts"]
  year: number
  month: number
  /** Un compte a été validé : la page recharge la revue. */
  onChanged: () => void
  /** « Tout valider » renvoie la revue complète : la page la remplace sans recharger. */
  onReview: (review: MonthReview) => void
}

/** « 2025-10-31 » → date courte dans la langue de l'interface, sans décalage de fuseau. */
function formatStatementDate(iso: string) {
  const [y, m, d] = iso.split("-").map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(appLocale())
}

export function AccountsStep({ step, year, month, onChanged, onReview }: AccountsStepProps) {
  const { t } = useTranslation("month")
  const [busyId, setBusyId] = useState<number | null>(null)
  const inputs = useRef(new Map<number, HTMLInputElement>())
  // Un compte validé aujourd'hui n'a plus bougé depuis : le backend le range alors dans `unchanged`.
  // Ceux validés pendant cette visite restent à leur place, avec « Validé », au lieu de changer de bloc.
  const [settledIds, setSettledIds] = useState<ReadonlySet<number>>(new Set())
  const settle = (id: number) => setSettledIds((prev) => new Set(prev).add(id))

  const isReconcile = (a: ReviewAccount) => a.group === "reconcile" || (a.group === "unchanged" && settledIds.has(a.id))
  const toReconcile = step.accounts.filter(isReconcile)
  const unchanged = step.accounts.filter((a) => a.group === "unchanged" && !isReconcile(a))
  const market = step.accounts.filter((a) => a.group === "market")

  async function verify(id: number) {
    setBusyId(id)
    try {
      await postAccountsVerify(id)
      settle(id)
      toast.success(t("accountsStep.soldeValide"))
      onChanged()
    } catch {
      toast.error(t("accountsStep.echecDeLaValidation"))
    } finally {
      setBusyId(null)
    }
  }

  /** Après un rapprochement réussi, le focus passe au prochain compte encore à saisir. */
  function focusNext(id: number) {
    const index = toReconcile.findIndex((a) => a.id === id)
    const next = toReconcile.slice(index + 1).find((a) => !a.verified_since_month_end && inputs.current.has(a.id))
    if (next) inputs.current.get(next.id)?.focus()
  }

  return (
    <Card>
      <CardContent className="space-y-6 p-4 md:p-6">
        <p className="text-sm text-slate-600">{t("accountsStep.comparezLeSoldeAfficheAvec")}</p>

        {toReconcile.length > 0 && (
          <section aria-labelledby="accounts-reconcile-title" className="space-y-2">
            <h3 id="accounts-reconcile-title" className="text-sm font-semibold text-slate-900">
              {t("accountsStep.aRapprocherAu", { date: formatStatementDate(toReconcile[0].statement_date) })}
            </h3>
            <ul className="space-y-2">
              {toReconcile.map((acc) => (
                <ReconcileRow
                  key={acc.id}
                  account={acc}
                  busy={busyId === acc.id}
                  inputRef={(el) => { if (el) inputs.current.set(acc.id, el); else inputs.current.delete(acc.id) }}
                  onVerify={() => verify(acc.id)}
                  onReconciled={() => { settle(acc.id); onChanged(); focusNext(acc.id) }}
                />
              ))}
            </ul>
          </section>
        )}

        <UnchangedBlock accounts={unchanged} year={year} month={month} onReview={onReview} />
        <MarketBlock accounts={market} busyId={busyId} onVerify={verify} />
      </CardContent>
    </Card>
  )
}
