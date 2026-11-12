import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { formatPeriodRange, type BudgetPeriod } from "@/lib/budgetPeriod"
import { getAnalyticsBudgetPeriod, putAnalyticsBudgetPeriod } from "@/lib/api/analytics"

export function BudgetPeriodCard() {
  const { t } = useTranslation("settings")
  const [period, setPeriod] = useState<BudgetPeriod | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getAnalyticsBudgetPeriod<BudgetPeriod>().then(setPeriod).catch(() => setPeriod(null))
  }, [])

  const salaryMode = period?.mode === "salary"

  async function toggle(checked: boolean) {
    setSaving(true)
    try {
      setPeriod(await putAnalyticsBudgetPeriod<BudgetPeriod>({ mode: checked ? "salary" : "civil" }))
      toast.success(checked ? t("budgetPeriodCard.moisDePaieActive") : t("budgetPeriodCard.moisCivilRetabli"))
    } catch {
      toast.error(t("budgetPeriodCard.impossibleDeChangerLeMode"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("budgetPeriodCard.decoupageDesMois")}</CardTitle>
        <CardDescription>
          {t("budgetPeriodCard.chaqueSalaireRecuOuvreUn")}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex items-center justify-between gap-4">
        <div className="min-w-0 text-sm text-slate-600">
          {salaryMode ? t("budgetPeriodCard.moisDePaie") : t("budgetPeriodCard.moisCivil")}
          {salaryMode && formatPeriodRange(period) && (
            <span className="block text-slate-400 sm:ml-2 sm:inline">{t("misc.currentPeriod", { range: formatPeriodRange(period) })}</span>
          )}
        </div>
        <Switch checked={salaryMode} disabled={saving || !period} onCheckedChange={toggle} />
      </CardContent>
    </Card>
  )
}
