import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { ReviewBudget } from "@/types/monthReview"

function Row({ label, value, extra }: { label: string; value: string; extra?: string }) {
  return (
    <div className="flex items-baseline justify-between py-2">
      <span className="text-sm text-slate-600">{label}</span>
      <span className="text-right">
        <span className="amount-blur font-semibold">{value}</span>
        {extra && <span className="amount-blur ml-2 text-xs text-slate-500">{extra}</span>}
      </span>
    </div>
  )
}

export function BudgetStep({ budget, onChanged }: { budget: ReviewBudget; onChanged: () => void }) {
  const hasExceptional = budget.exceptional_expenses > 0
  const diff = budget.real_expenses - budget.previous_real_expenses
  const overruns = budget.alerts.filter((a) => a.monthly_ratio !== null && a.monthly_ratio >= 1)

  async function toggle(id: number, value: boolean) {
    try {
      await api.patch(`/transactions/${id}`, { is_exceptional: value })
      toast.success(value ? "Marquée exceptionnelle" : "Marquage retiré")
      onChanged()
    } catch {
      toast.error("Échec de la mise à jour")
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="divide-y p-6">
          <Row label="Revenus" value={formatCurrency(budget.income)} />
          <Row
            label="Dépenses réelles"
            value={formatCurrency(budget.real_expenses)}
            extra={`${diff >= 0 ? "+" : ""}${formatCurrency(diff)} vs mois précédent`}
          />
          {hasExceptional && (
            <Row
              label="Dépenses hors exceptionnelles"
              value={formatCurrency(budget.real_expenses_excl_exceptional)}
              extra={`dont ${formatCurrency(budget.exceptional_expenses)} exceptionnelles`}
            />
          )}
          <Row
            label="Épargne du mois"
            value={formatCurrency(budget.savings)}
            extra={hasExceptional ? `${formatCurrency(budget.savings_excl_exceptional)} hors exceptionnelles` : undefined}
          />
          <Row
            label="Taux d'épargne"
            value={`${budget.savings_rate.toFixed(1)} %`}
            extra={hasExceptional ? `${budget.savings_rate_excl_exceptional.toFixed(1)} % hors exceptionnelles` : undefined}
          />
          <Row
            label="Burn rate (par jour)"
            value={formatCurrency(budget.burn_rate)}
            extra={hasExceptional ? `${formatCurrency(budget.burn_rate_excl_exceptional)} hors exceptionnelles` : undefined}
          />
        </CardContent>
      </Card>

      {overruns.length > 0 && (
        <Card>
          <CardContent className="space-y-2 p-6">
            <p className="text-sm font-semibold">Budgets dépassés</p>
            {overruns.map((a) => (
              <div key={a.category_id} className="flex justify-between text-sm">
                <span>{a.category_name}</span>
                <span className="amount-blur text-rose-600">
                  {formatCurrency(a.monthly_spent)} / {formatCurrency(a.monthly_limit ?? 0)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="space-y-3 p-6">
          <p className="text-sm text-slate-600">
            Plus grosses dépenses du mois. Marquez un achat ponctuel comme <strong>exceptionnel</strong> pour
            juger le mois sans lui (il reste dans les totaux et les soldes).
          </p>
          <ul className="divide-y">
            {budget.top_expenses.map((tx) => (
              <li key={tx.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="font-medium">{tx.merchant}</p>
                  <p className="text-xs text-slate-500">
                    {new Date(tx.date).toLocaleDateString("fr-FR")}
                    {tx.category_name ? ` · ${tx.category_name}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="amount-blur font-semibold">{formatCurrency(tx.amount)}</span>
                  <Button
                    size="sm"
                    variant={tx.is_exceptional ? "default" : "outline"}
                    onClick={() => toggle(tx.id, !tx.is_exceptional)}
                  >
                    {tx.is_exceptional ? "Exceptionnelle" : "Marquer exceptionnelle"}
                  </Button>
                </div>
              </li>
            ))}
            {budget.top_expenses.length === 0 && (
              <li className="py-3 text-sm text-slate-500">Aucune dépense ce mois-ci.</li>
            )}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
