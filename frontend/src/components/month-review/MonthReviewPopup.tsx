import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { safeStorage } from "@/lib/storage"
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ClipboardCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { fetchCurrentBudgetMonth } from "@/lib/budgetPeriod"
import type { MonthClosureSummary, MonthReview } from "@/types/monthReview"
import { getMonthReview, getMonthReviewClosures } from "@/lib/api/monthReview"

// Confort par appareil : le stockage peut être indisponible, la pop-up fonctionne sans.
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
    /* stockage indisponible : la pop-up reviendra, sans conséquence */
  }
}

const todayKey = () => new Date().toLocaleDateString("sv-SE")

export function MonthReviewPopup() {
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

  if (!review) return null

  const suffix = `${review.year}-${review.month}`
  const label = new Date(review.year, review.month - 1, 1).toLocaleDateString(appLocale(), { month: "long" })
  const points = review.categorize.count + review.accounts.unverified_count

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 pr-6 text-left">
            <ClipboardCheck className="h-5 w-5 text-emerald-600" />
            {/* `capitalize` mettait une majuscule à chaque mot : seul le mois en prend une */}
            {i18n.t("misc.popupTitle", { ns: "month", month: label.charAt(0).toUpperCase() + label.slice(1) })}
          </DialogTitle>
          <DialogDescription>
            {points > 0
              ? i18n.t("misc.popupPoints", { ns: "month", expenses: review.categorize.count, accounts: review.accounts.unverified_count })
              : t("monthReviewPopup.toutSembleEnOrdreIl")}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:justify-between">
          <Button
            variant="ghost"
            className="h-11 sm:h-10"
            onClick={() => {
              writeStorage(`month-review-skip-${suffix}`, "1")
              setOpen(false)
            }}
          >
            {t("monthReviewPopup.pasCeMoisCi")}
          </Button>
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <Button
              variant="outline"
              className="h-11 sm:h-10"
              onClick={() => {
                writeStorage(`month-review-snooze-${suffix}`, todayKey())
                setOpen(false)
              }}
            >
              {t("monthReviewPopup.plusTard")}
            </Button>
            <Button className="h-11 sm:h-10" onClick={() => navigate(`/month/revue?year=${review.year}&month=${review.month}`)}>
              {t("monthReviewPopup.faireLaRevue")}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
