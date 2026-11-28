/** Comptes bancaires sans transaction depuis leur dernière vérification : validés tous ensemble en un clic. */
import { useTranslation } from "react-i18next"
import { CheckCircle2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { useSubmit } from "@/hooks/useSubmit"
import { postMonthReviewAccountsConfirmUnchanged } from "@/lib/api/monthReview"
import { errorMessage } from "@/lib/utils"
import type { MonthReview, ReviewAccount } from "@/types/monthReview"

interface Props {
  accounts: ReviewAccount[]
  year: number
  month: number
  onReview: (review: MonthReview) => void
}

export function UnchangedBlock({ accounts, year, month, onReview }: Props) {
  const { t } = useTranslation("month")
  const [confirmAll, busy] = useSubmit(async () => {
    try {
      const review = await postMonthReviewAccountsConfirmUnchanged<MonthReview>({ year, month })
      toast.success(t("accountsStep.comptesValides"))
      onReview(review)
    } catch (e) {
      toast.error(errorMessage(e, t("accountsStep.echecDeLaValidation")))
    }
  })

  if (accounts.length === 0) return null
  const pending = accounts.some((a) => !a.verified_since_month_end)

  return (
    <section aria-labelledby="accounts-unchanged-title" className="space-y-2">
      <h3 id="accounts-unchanged-title" className="text-sm font-semibold text-slate-900">
        {t("accountsStep.rienNABouge", { count: accounts.length })}
      </h3>
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="min-w-0 text-sm text-slate-700">{accounts.map((a) => a.name).join(" · ")}</p>
        {pending ? (
          <Button size="sm" variant="outline" className="h-10 shrink-0 md:h-9" disabled={busy} onClick={() => confirmAll()}>
            {t("accountsStep.toutValider")}
          </Button>
        ) : (
          <span className="flex shrink-0 items-center gap-1 text-sm text-emerald-700">
            <CheckCircle2 className="h-4 w-4" /> {t("accountsStep.valide")}
          </span>
        )}
      </div>
    </section>
  )
}
