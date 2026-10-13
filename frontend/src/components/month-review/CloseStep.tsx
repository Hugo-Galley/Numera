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
  const unresolved = review.categorize.count + review.accounts.unverified_count

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        {review.closed && review.closure && (
          <div className="flex items-start gap-3 rounded-lg bg-emerald-50 p-4 text-emerald-800">
            <CheckCircle2 className="mt-0.5 h-5 w-5" />
            <div className="text-sm">
              <p className="font-semibold">
                Clôturé le {new Date(review.closure.closed_at).toLocaleDateString("fr-FR")}
              </p>
              {review.closure.unresolved_count > 0 && (
                <p>{review.closure.unresolved_count} point(s) restaient à traiter à la clôture.</p>
              )}
            </div>
          </div>
        )}
        {review.modified_since_close && (
          <div className="flex items-start gap-3 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-5 w-5" />
            Des transactions ont changé depuis la clôture. Vous pouvez re-clôturer pour mettre la photo à jour.
          </div>
        )}

        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-slate-500">Dépenses sans catégorie</dt>
            <dd className="font-semibold">{review.categorize.count}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Comptes à valider</dt>
            <dd className="font-semibold">{review.accounts.unverified_count}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Dépenses réelles</dt>
            <dd className="amount-blur font-semibold">{formatCurrency(review.budget.real_expenses)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Épargne</dt>
            <dd className="amount-blur font-semibold">{formatCurrency(review.budget.savings)}</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-slate-500">Fait marquant</dt>
            <dd className="font-medium">{highlight.trim() || "—"}</dd>
          </div>
        </dl>

        {unresolved > 0 && !review.closed && (
          <p className="text-sm text-slate-500">
            Il reste {unresolved} point(s) à traiter ; vous pouvez tout de même clôturer, ils seront notés.
          </p>
        )}

        <div className="flex flex-wrap gap-3">
          <Button onClick={onClose} disabled={busy}>
            {review.closed ? "Re-clôturer le mois" : "Clôturer le mois"}
          </Button>
          {review.closed && (
            <Button variant="outline" onClick={onReopen} disabled={busy}>
              Rouvrir le mois
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
