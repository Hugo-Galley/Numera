/** Fin du parcours : le mois est clôturé, avec un récapitulatif court et la suite (bilan, réouverture). */
import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { AlertTriangle, CheckCircle2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { appLocale } from "@/i18n/locale"
import { formatCurrency } from "@/lib/utils"
import type { MonthReview } from "@/types/monthReview"

interface Props {
  review: MonthReview
  /** Nom du mois dans la langue de l'interface, avec une majuscule (« Juin »). */
  monthName: string
  busy: boolean
  onReclose: () => void
  onReopen: () => void
}

export function MonthClosed({ review, monthName, busy, onReclose, onReopen }: Props) {
  const { t } = useTranslation("month")
  const { budget, closure } = review
  const figures = [
    { label: t("monthReview.revenus"), value: budget.income, tone: "text-emerald-700" },
    { label: t("closeStep.depensesReelles"), value: budget.real_expenses, tone: "text-rose-700" },
    { label: t("closeStep.epargne"), value: budget.savings, tone: "text-slate-900" },
  ]

  return (
    <Card className="border-emerald-200">
      <CardContent className="space-y-6 p-6 text-center md:p-10">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 animate-in zoom-in-50 fade-in duration-500">
          <CheckCircle2 className="h-9 w-9" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-black tracking-tight md:text-3xl">{t("monthReview.closedTitle", { month: monthName })}</h2>
          {closure && (
            <p className="text-sm text-slate-500">
              {i18n.t("misc.closedOn", { ns: "month", date: new Date(closure.closed_at).toLocaleDateString(appLocale()) })}
              {closure.unresolved_count > 0 && ` · ${t("monthReview.closedUnresolved", { count: closure.unresolved_count })}`}
            </p>
          )}
          <p className="mx-auto max-w-md text-sm text-slate-600">{t("monthReview.closedHint")}</p>
        </div>

        <dl className="mx-auto grid max-w-lg grid-cols-1 gap-3 sm:grid-cols-3">
          {figures.map((f) => (
            <div key={f.label} className="rounded-xl bg-slate-50 p-3">
              <dt className="text-xs text-slate-500">{f.label}</dt>
              <dd className={`amount-blur text-lg font-black tabular-nums ${f.tone}`}>{formatCurrency(f.value)}</dd>
            </div>
          ))}
        </dl>

        {review.modified_since_close && (
          <div className="mx-auto flex max-w-lg items-start gap-3 rounded-lg bg-amber-50 p-4 text-left text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="space-y-2">
              <p>{t("closeStep.desTransactionsOntChangeDepuis")}</p>
              <Button size="sm" variant="outline" className="h-10 md:h-9" onClick={onReclose} disabled={busy}>
                {t("closeStep.reCloturerLeMois")}
              </Button>
            </div>
          </div>
        )}

        <div className="flex flex-col items-center gap-2 sm:flex-row sm:justify-center">
          <Button asChild className="h-11 w-full sm:h-10 sm:w-auto">
            <Link to={`/month/bilan?year=${review.year}&month=${review.month}`}>{t("monthReview.voirLeBilan")}</Link>
          </Button>
          <Button variant="ghost" className="h-11 w-full text-slate-500 sm:h-10 sm:w-auto" onClick={onReopen} disabled={busy}>
            {t("closeStep.rouvrirLeMois")}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
