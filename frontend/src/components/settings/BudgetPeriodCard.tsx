import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { api } from "@/lib/api"
import { formatPeriodRange, type BudgetPeriod } from "@/lib/budgetPeriod"

export function BudgetPeriodCard() {
  const [period, setPeriod] = useState<BudgetPeriod | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get<BudgetPeriod>("/analytics/budget-period").then(setPeriod).catch(() => setPeriod(null))
  }, [])

  const salaryMode = period?.mode === "salary"

  async function toggle(checked: boolean) {
    setSaving(true)
    try {
      setPeriod(await api.put<BudgetPeriod>("/analytics/budget-period", { mode: checked ? "salary" : "civil" }))
      toast.success(checked ? "Mois de paie activé" : "Mois civil rétabli")
    } catch {
      toast.error("Impossible de changer le mode de découpage")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Découpage des mois</CardTitle>
        <CardDescription>
          Chaque salaire reçu ouvre un nouveau mois : le salaire du 25 août finance septembre, comme les
          investissements du 29. Les dates et les soldes des transactions ne changent pas.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex items-center justify-between gap-4">
        <div className="min-w-0 text-sm text-slate-600">
          {salaryMode ? "Mois de paie" : "Mois civil"}
          {salaryMode && formatPeriodRange(period) && (
            <span className="block text-slate-400 sm:ml-2 sm:inline">Période en cours : {formatPeriodRange(period)}</span>
          )}
        </div>
        <Switch checked={salaryMode} disabled={saving || !period} onCheckedChange={toggle} />
      </CardContent>
    </Card>
  )
}
