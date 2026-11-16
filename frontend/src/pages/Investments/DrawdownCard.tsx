import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { TrendingDown } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { getAnalyticsPortfolio } from "@/lib/api/analytics"
import type { ApiResponse } from "@/lib/api/types"
import { formatRate } from "@/lib/utils"
import { appLocale } from "@/i18n/locale"

type Drawdown = NonNullable<ApiResponse<"/analytics/portfolio", "get">["drawdown"]>

const day = (iso: string | null | undefined) => (iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(appLocale()) : "-")

/** Pire baisse de l'ensemble des comptes titres, mesurée sur la performance neutre des versements. */
export function DrawdownCard() {
  const { t } = useTranslation("investments")
  const [drawdown, setDrawdown] = useState<Drawdown | null>(null)

  useEffect(() => {
    let cancelled = false
    getAnalyticsPortfolio()
      .then((overview) => { if (!cancelled) setDrawdown(overview.drawdown ?? null) })
      .catch(() => { /* carte facultative : la page reste utilisable sans elle */ })
    return () => { cancelled = true }
  }, [])

  if (!drawdown) return null

  return (
    <Card data-testid="drawdown-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <TrendingDown className="h-5 w-5 text-rose-600" />
          {t("drawdown.title")}
        </CardTitle>
        <CardDescription>{t("drawdown.subtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-slate-500">{t("drawdown.max")}</p>
          <p className={`text-2xl font-black tabular-nums ${drawdown.max_drawdown_pct < 0 ? "text-rose-600" : "text-slate-900"}`}>
            {formatRate(drawdown.max_drawdown_pct, 1)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500">{t("drawdown.period")}</p>
          <p className="font-semibold">
            {drawdown.trough_date ? t("drawdown.fromTo", { peak: day(drawdown.peak_date), trough: day(drawdown.trough_date) }) : t("drawdown.none")}
          </p>
          {drawdown.trough_date && (
            <p className="text-xs text-slate-500">
              {drawdown.recovery_date ? t("drawdown.recovered", { date: day(drawdown.recovery_date) }) : t("drawdown.notRecovered")}
            </p>
          )}
        </div>
        <div>
          <p className="text-xs text-slate-500">{t("drawdown.current")}</p>
          <p className={`text-lg font-bold tabular-nums ${drawdown.current_drawdown_pct < 0 ? "text-rose-600" : "text-emerald-600"}`}>
            {drawdown.current_drawdown_pct < 0 ? formatRate(drawdown.current_drawdown_pct, 1) : t("drawdown.atPeak")}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
