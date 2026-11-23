import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { safeStorage } from "@/lib/storage"
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ClipboardCheck, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { fetchCurrentBudgetMonth } from "@/lib/budgetPeriod"
import type { MonthClosureSummary, MonthReview } from "@/types/monthReview"
import { getMonthReview, getMonthReviewClosures } from "@/lib/api/monthReview"

// Confort par appareil : le stockage peut être indisponible, le rappel fonctionne sans.
function readStorage(key: string): string | null {
  try {
    return safeStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key: string, value: string) {
  try {
    safeStorage.setItem(key, value)
  } catch {
    /* stockage indisponible : le rappel reviendra, sans conséquence */
  }
}

const todayKey = () => new Date().toLocaleDateString("sv-SE")

export function MonthReviewReminder() {
  const { t } = useTranslation("month")
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [review, setReview] = useState<MonthReview | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        // Mois de paie : la revue porte sur le mois budgétaire qui précède celui en cours.
        const current = (await fetchCurrentBudgetMonth()) ?? {
          year: new Date().getFullYear(),
          month: new Date().getMonth() + 1,
        }
        const previous = new Date(current.year, current.month - 2, 1)
        const target = { year: previous.getFullYear(), month: previous.getMonth() + 1 }
        const suffix = `${target.year}-${target.month}`
        if (readStorage(`month-review-skip-${suffix}`) === "1") return
        if (readStorage(`month-review-snooze-${suffix}`) === todayKey()) return

        const closures = await getMonthReviewClosures<MonthClosureSummary[]>()
        if (closures.some((c) => c.year === target.year && c.month === target.month)) return
        const data = await getMonthReview<MonthReview>(`?year=${target.year}&month=${target.month}`)
        const hasActivity = data.budget.income > 0 || data.budget.real_expenses > 0 || data.categorize.count > 0
        if (!cancelled && hasActivity) {
          setReview(data)
          setOpen(true)
        }
      } catch {
        /* confort : aucun message en cas d'échec */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (!review || !open) return null

  const suffix = `${review.year}-${review.month}`
  const label = new Date(review.year, review.month - 1, 1).toLocaleDateString(appLocale(), { month: "long" })
  const points = review.categorize.count + review.accounts.unverified_count

  // Bandeau discret dans la page (plus de fenêtre modale à chaque connexion) : il ne bloque rien
  return (
    <section
      aria-label={t("monthReviewPopup.label")}
      className="flex flex-col gap-2 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-sm sm:flex-row sm:items-center sm:gap-3"
    >
      <div className="flex min-w-0 flex-1 items-start gap-2">
        <ClipboardCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
        <p className="min-w-0 text-slate-700">
          {/* `capitalize` mettait une majuscule à chaque mot : seul le mois en prend une */}
          <span className="font-semibold text-slate-900">
            {i18n.t("misc.popupTitle", { ns: "month", month: label.charAt(0).toUpperCase() + label.slice(1) })}
          </span>{" "}
          {points > 0
            ? i18n.t("misc.popupPoints", { ns: "month", expenses: review.categorize.count, accounts: review.accounts.unverified_count })
            : t("monthReviewPopup.toutSembleEnOrdreIl")}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1 self-end sm:self-auto">
        <Button
          variant="ghost"
          size="sm"
          className="h-10 sm:h-8"
          onClick={() => {
            writeStorage(`month-review-snooze-${suffix}`, todayKey())
            setOpen(false)
          }}
        >
          {t("monthReviewPopup.plusTard")}
        </Button>
        <Button size="sm" className="h-10 sm:h-8" onClick={() => navigate(`/month/revue?year=${review.year}&month=${review.month}`)}>
          {t("monthReviewPopup.faireLaRevue")}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 sm:h-8 sm:w-8 text-slate-500"
          aria-label={t("monthReviewPopup.ignorer")}
          title={t("monthReviewPopup.ignorer")}
          onClick={() => {
            writeStorage(`month-review-skip-${suffix}`, "1")
            setOpen(false)
          }}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </section>
  )
}
