/** Placements (investissement, assurance vie) : valeur actuelle et simple validation, sans rapprochement. */
import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { CheckCircle2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { appLocale } from "@/i18n/locale"
import { formatCurrency } from "@/lib/utils"
import type { ReviewAccount } from "@/types/monthReview"

interface Props {
  accounts: ReviewAccount[]
  busyId: number | null
  onVerify: (id: number) => void
}

export function MarketBlock({ accounts, busyId, onVerify }: Props) {
  const { t } = useTranslation("month")
  if (accounts.length === 0) return null

  return (
    <section aria-labelledby="accounts-market-title" className="space-y-2">
      <h3 id="accounts-market-title" className="text-sm font-semibold text-slate-900">{t("accountsStep.placements")}</h3>
      <ul className="space-y-2">
        {accounts.map((acc) => (
          <li key={acc.id} className="flex flex-col gap-3 rounded-xl border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="truncate font-medium">{acc.name}</p>
              <p className="text-xs text-slate-500">
                {i18n.t("misc.lastValidation", { ns: "month", date: new Date(acc.last_verified_at).toLocaleDateString(appLocale()) })}
              </p>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="amount-blur whitespace-nowrap font-semibold tabular-nums">{formatCurrency(acc.balance, acc.currency)}</span>
              {acc.verified_since_month_end ? (
                <span className="flex items-center gap-1 text-sm text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" /> {t("accountsStep.valide")}
                </span>
              ) : (
                <Button size="sm" variant="outline" className="h-10 md:h-9" disabled={busyId === acc.id} onClick={() => onVerify(acc.id)}>
                  {t("accountsStep.validerLeSolde")}
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
