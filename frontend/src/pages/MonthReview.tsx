import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { ChevronLeft, ChevronRight, ClipboardCheck } from "lucide-react"
import { toast } from "sonner"

import { AccountsStep } from "@/components/month-review/AccountsStep"
import { BudgetStep } from "@/components/month-review/BudgetStep"
import { CategorizeStep } from "@/components/month-review/CategorizeStep"
import { CloseStep } from "@/components/month-review/CloseStep"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { fetchCurrentBudgetMonth } from "@/lib/budgetPeriod"
import type { MonthReview as MonthReviewData } from "@/types/monthReview"

const STEPS = ["Catégoriser", "Soldes", "Budget", "Fait marquant", "Clôturer"] as const

function previousMonth() {
  const d = new Date()
  d.setDate(1)
  d.setMonth(d.getMonth() - 1)
  return { year: d.getFullYear(), month: d.getMonth() + 1 }
}

export default function MonthReview() {
  const [params, setParams] = useSearchParams()
  const [fallback, setFallback] = useState(previousMonth)
  // Mois de paie : le dernier mois terminé est celui qui précède le mois budgétaire en cours.
  useEffect(() => {
    fetchCurrentBudgetMonth().then(current => {
      if (current) {
        const d = new Date(current.year, current.month - 2, 1)
        setFallback({ year: d.getFullYear(), month: d.getMonth() + 1 })
      }
    })
  }, [])
  const year = Number(params.get("year")) || fallback.year
  const month = Number(params.get("month")) || fallback.month

  const [review, setReview] = useState<MonthReviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState(0)
  const [highlight, setHighlight] = useState("")
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api.get<MonthReviewData>(`/month-review?year=${year}&month=${month}`)
      setReview(data)
      setHighlight((current) => current || data.closure?.highlight || "")
    } catch {
      toast.error("Impossible de charger la revue du mois")
    }
  }, [year, month])

  useEffect(() => {
    setLoading(true)
    setHighlight("")
    load().finally(() => setLoading(false))
  }, [load])

  function go(delta: number) {
    const d = new Date(year, month - 1 + delta, 1)
    setParams({ year: String(d.getFullYear()), month: String(d.getMonth() + 1) })
    setStep(0)
  }

  async function closeMonth() {
    setBusy(true)
    try {
      const data = await api.post<MonthReviewData>("/month-review/close", {
        year,
        month,
        highlight: highlight.trim() || null,
      })
      setReview(data)
      toast.success("Mois clôturé")
    } catch {
      toast.error("Échec de la clôture")
    } finally {
      setBusy(false)
    }
  }

  async function reopenMonth() {
    setBusy(true)
    try {
      await api.delete(`/month-review?year=${year}&month=${month}`)
      toast.success("Mois rouvert")
      await load()
    } catch {
      toast.error("Échec de la réouverture")
    } finally {
      setBusy(false)
    }
  }

  const label = new Date(year, month - 1, 1).toLocaleDateString("fr-FR", { month: "long", year: "numeric" })

  function status(i: number): "ok" | "todo" | "neutral" {
    if (!review) return "neutral"
    if (i === 0) return review.categorize.count === 0 ? "ok" : "todo"
    if (i === 1) return review.accounts.unverified_count === 0 ? "ok" : "todo"
    if (i === 3) return highlight.trim() ? "ok" : "neutral"
    if (i === 4) return review.closed ? "ok" : "neutral"
    return "neutral"
  }

  return (
    <div className="space-y-6 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
            <ClipboardCheck className="h-7 w-7 text-emerald-600" />
            Revue de mois
          </h1>
          <p className="text-slate-500">Passez le mois en revue, étape par étape, puis clôturez-le.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => go(-1)} aria-label="Mois précédent">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="min-w-36 text-center font-semibold capitalize">{label}</span>
          <Button variant="outline" size="icon" onClick={() => go(1)} aria-label="Mois suivant">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {STEPS.map((name, i) => {
          const s = status(i)
          return (
            <button
              key={name}
              onClick={() => setStep(i)}
              className={cn(
                "rounded-full border px-4 py-1.5 text-sm transition-colors",
                step === i ? "border-slate-900 bg-slate-900 text-white" : "bg-white hover:bg-slate-50",
                step !== i && s === "ok" && "border-emerald-200 text-emerald-700",
                step !== i && s === "todo" && "border-amber-300 text-amber-700"
              )}
            >
              {i + 1}. {name}
            </button>
          )
        })}
      </div>

      {loading || !review ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          {step === 0 && <CategorizeStep step={review.categorize} onChanged={load} />}
          {step === 1 && <AccountsStep step={review.accounts} onChanged={load} />}
          {step === 2 && <BudgetStep budget={review.budget} onChanged={load} />}
          {step === 3 && (
            <Card>
              <CardContent className="space-y-3 p-6">
                <label htmlFor="highlight" className="text-sm text-slate-600">
                  Un fait marquant à retenir de ce mois (optionnel) : résiliation, grosse dépense, changement d'épargne…
                </label>
                <textarea
                  id="highlight"
                  value={highlight}
                  maxLength={500}
                  onChange={(e) => setHighlight(e.target.value)}
                  rows={4}
                  className="w-full rounded-md border border-slate-200 bg-white p-3 text-sm"
                />
              </CardContent>
            </Card>
          )}
          {step === 4 && (
            <CloseStep
              review={review}
              highlight={highlight}
              busy={busy}
              onClose={closeMonth}
              onReopen={reopenMonth}
            />
          )}
        </>
      )}
    </div>
  )
}
