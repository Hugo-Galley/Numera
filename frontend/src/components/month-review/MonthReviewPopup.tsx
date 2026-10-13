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
import { api } from "@/lib/api"
import type { MonthClosureSummary, MonthReview } from "@/types/monthReview"

// Confort par appareil : le stockage peut être indisponible, la pop-up fonctionne sans.
function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* stockage indisponible : la pop-up reviendra, sans conséquence */
  }
}

const todayKey = () => new Date().toLocaleDateString("sv-SE")

export function MonthReviewPopup() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [review, setReview] = useState<MonthReview | null>(null)

  useEffect(() => {
    let cancelled = false
    const now = new Date()
    const target =
      now.getMonth() === 0
        ? { year: now.getFullYear() - 1, month: 12 }
        : { year: now.getFullYear(), month: now.getMonth() }
    const suffix = `${target.year}-${target.month}`
    if (readStorage(`month-review-skip-${suffix}`) === "1") return
    if (readStorage(`month-review-snooze-${suffix}`) === todayKey()) return

    ;(async () => {
      try {
        const closures = await api.get<MonthClosureSummary[]>("/month-review/closures")
        if (closures.some((c) => c.year === target.year && c.month === target.month)) return
        const data = await api.get<MonthReview>(`/month-review?year=${target.year}&month=${target.month}`)
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
  const label = new Date(review.year, review.month - 1, 1).toLocaleDateString("fr-FR", { month: "long" })
  const points = review.categorize.count + review.accounts.unverified_count

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 capitalize">
            <ClipboardCheck className="h-5 w-5 text-emerald-600" />
            {label} n'est pas encore clôturé
          </DialogTitle>
          <DialogDescription>
            {points > 0
              ? `${review.categorize.count} dépense(s) sans catégorie et ${review.accounts.unverified_count} compte(s) à valider.`
              : "Tout semble en ordre : il ne reste qu'à vérifier le budget et à clôturer."}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:justify-between">
          <Button
            variant="ghost"
            onClick={() => {
              writeStorage(`month-review-skip-${suffix}`, "1")
              setOpen(false)
            }}
          >
            Pas ce mois-ci
          </Button>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                writeStorage(`month-review-snooze-${suffix}`, todayKey())
                setOpen(false)
              }}
            >
              Plus tard
            </Button>
            <Button onClick={() => navigate(`/month-review?year=${review.year}&month=${review.month}`)}>
              Faire la revue
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
