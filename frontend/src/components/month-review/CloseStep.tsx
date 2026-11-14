import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { AlertTriangle, CheckCircle2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import type { MonthReview } from "@/types/monthReview"

export function CloseStep({
  review,
  highlight,
  busy,
  onClose,
  onReopen,
}: {
  review: MonthReview
  highlight: string
  busy: boolean
  onClose: () => void
  onReopen: () => void
}) {
  const { t } = useTranslation("month")
  const unresolved = review.categorize.count + review.accounts.unverified_count

  return (
    <Card>
      <CardContent className="space-y-4 p-4 md:p-6">
        {review.closed && review.closure && (
          <div className="flex items-start gap-3 rounded-lg bg-emerald-50 p-4 text-emerald-800">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="text-sm">
              <p className="font-semibold">
                {i18n.t("misc.closedOn", { ns: "month", date: new Date(review.closure.closed_at).toLocaleDateString(appLocale()) })}
              </p>
              {review.closure.unresolved_count > 0 && (
                <p>{review.closure.unresolved_count} point(s) restaient à traiter à la clôture.</p>
              )}
            </div>
          </div>
        )}
        {review.modified_since_close && (
          <div className="flex items-start gap-3 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
            {t("closeStep.desTransactionsOntChangeDepuis")}
          </div>
        )}

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

        {unresolved > 0 && !review.closed && (
          <p className="text-sm text-slate-500">
            {i18n.t("misc.unresolved", { ns: "month", count: unresolved })}
          </p>
        )}

        <div className="flex flex-col gap-3 sm:flex-row">
          <Button className="h-11 sm:h-10" onClick={onClose} disabled={busy}>
            {review.closed ? t("closeStep.reCloturerLeMois") : t("closeStep.cloturerLeMois")}
          </Button>
          {review.closed && (
            <Button variant="outline" className="h-11 sm:h-10" onClick={onReopen} disabled={busy}>
              {t("closeStep.rouvrirLeMois")}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
