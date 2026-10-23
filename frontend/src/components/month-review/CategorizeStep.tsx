import { useEffect, useState } from "react"
import { CheckCircle2 } from "lucide-react"
import { toast } from "sonner"

import { Card, CardContent } from "@/components/ui/card"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { MonthReview } from "@/types/monthReview"

interface CategoryOption {
  id: number
  name: string
  type?: string
}

export function CategorizeStep({
  step,
  onChanged,
}: {
  step: MonthReview["categorize"]
  onChanged: () => void
}) {
  const [categories, setCategories] = useState<CategoryOption[]>([])

  useEffect(() => {
    // L'étape ne traite que des dépenses : pas de Salaire ni de Dividendes dans la liste
    api.get<CategoryOption[]>("/categories")
      .then((all) => setCategories(all.filter((c) => c.type !== "revenu")))
      .catch(() => setCategories([]))
  }, [])

  async function assign(id: number, categoryId: string) {
    if (!categoryId) return
    try {
      await api.patch(`/transactions/${id}`, { category_id: Number(categoryId) })
      toast.success("Catégorie enregistrée")
      onChanged()
    } catch {
      toast.error("Échec de la catégorisation")
    }
  }

  if (step.count === 0) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-6 text-emerald-700">
          <CheckCircle2 className="h-5 w-5" />
          Toutes les dépenses du mois sont catégorisées.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="space-y-4 p-4 md:p-6">
        <p className="text-sm text-slate-600">
          {step.count} dépense{step.count > 1 ? "s" : ""} sans catégorie, soit{" "}
          <span className="amount-blur font-semibold">{formatCurrency(step.total)}</span>.
          {step.count > step.items.length && ` Les ${step.items.length} plus grosses sont listées.`}
        </p>
        <ul className="divide-y">
          {step.items.map((tx) => (
            <li key={tx.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
              <div className="flex items-baseline justify-between gap-3 sm:block sm:min-w-0">
                <p className="min-w-0 truncate font-medium">{tx.merchant}</p>
                <p className="shrink-0 text-xs text-slate-500">{new Date(tx.date).toLocaleDateString("fr-FR")}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="amount-blur order-2 whitespace-nowrap font-semibold tabular-nums sm:order-none">{formatCurrency(tx.amount)}</span>
                <select
                  defaultValue=""
                  onChange={(e) => assign(tx.id, e.target.value)}
                  className="h-11 min-w-0 flex-1 rounded-md border border-slate-200 bg-white px-2 text-base sm:h-9 sm:flex-none sm:text-sm"
                  aria-label={`Catégorie de ${tx.merchant}`}
                >
                  <option value="">Choisir…</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
