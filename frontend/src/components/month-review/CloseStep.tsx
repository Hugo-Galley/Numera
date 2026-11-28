import i18n from "i18next"
import { useTranslation } from "react-i18next"

import { Card, CardContent } from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import type { MonthReview } from "@/types/monthReview"

/** Dernière étape avant clôture : ce qui reste et ce qui sera retenu. Le bouton « Clôturer le mois » est dans `StepNav`. */
export function CloseStep({ review, highlight }: { review: MonthReview; highlight: string }) {
  const { t } = useTranslation("month")
  const unresolved = review.categorize.count + review.accounts.unverified_count

  return (
    <Card>
      <CardContent className="space-y-4 p-4 md:p-6">
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-slate-500">{t("closeStep.depensesSansCategorie")}</dt>
            <dd className="font-semibold">{review.categorize.count}</dd>
          </div>
          <div>
            <dt className="text-slate-500">{t("closeStep.comptesAValider")}</dt>
            <dd className="font-semibold">{review.accounts.unverified_count}</dd>
          </div>
          <div>
            <dt className="text-slate-500">{t("closeStep.depensesReelles")}</dt>
            <dd className="amount-blur font-semibold">{formatCurrency(review.budget.real_expenses)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">{t("closeStep.epargne")}</dt>
            <dd className="amount-blur font-semibold">{formatCurrency(review.budget.savings)}</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-slate-500">{t("closeStep.faitMarquant")}</dt>
            <dd className="wrap-break-word font-medium">{highlight.trim() || "—"}</dd>
          </div>
        </dl>

        {unresolved > 0 && (
          <p className="text-sm text-slate-500">
            {i18n.t("misc.unresolved", { ns: "month", count: unresolved })}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
